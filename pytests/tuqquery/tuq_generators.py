import re

class TuqGenerators(object):
    
    def __init__(self, log, full_set):
        self.log = log
        self.full_set = full_set
        self.query = None
        self.type_args = {}
        self.type_args['str'] = [attr[0] for attr in full_set[0].iteritems()
                            if isinstance(attr[1], unicode)]
        self.type_args['int'] = [attr[0] for attr in full_set[0].iteritems()
                            if isinstance(attr[1], int)]
        self.type_args['float'] = [attr[0] for attr in full_set[0].iteritems()
                            if isinstance(attr[1], float)]
        self.type_args['bool'] = [attr[0] for attr in full_set[0].iteritems()
                            if isinstance(attr[1], bool)]
        self.type_args['list_str'] = [attr[0] for attr in full_set[0].iteritems()
                            if isinstance(attr[1], list) and isinstance(attr[1][0], unicode)]
        self.type_args['list_obj'] = [attr[0] for attr in full_set[0].iteritems()
                            if isinstance(attr[1], list) and isinstance(attr[1][0], dict)]
        self.type_args['obj'] = [attr[0] for attr in full_set[0].iteritems()
                             if isinstance(attr[1], dict)]
        self.distict = False
        self.aggr_fns = {}

    def generate_query(self, template):
        query = template
        for name_type, type_arg in self.type_args.iteritems():
            for attr_type_arg in type_arg:
                query = query.replace('$%s%s' % (name_type, type_arg.index(attr_type_arg)), attr_type_arg)
        for expr in [' where ', ' select ', ' from ', ' order by', ' limit ', ' offset ', ' count(']:
            query = query.replace(expr, expr.upper())
        self.log.info("Generated query to be run: '''%s'''" % query)
        self.query = query
        return query

    def generate_expected_result(self):
        where_clause = self._format_where_clause()
        select_clause = self._format_select_clause()
        result = self._filter_full_set(select_clause, where_clause)
        result = self._order_results(result)
        result = self._limit_and_offset(result)
        return result


    def _format_where_clause(self):
        if self.query.find('WHERE') == -1:
            return None
        clause = re.sub(r'.*ORDER BY', '', re.sub(r'.*WHERE', '', self.query)).strip()
        attributes = [attr for group in self.type_args.itervalues() for attr in group]
        conditions = clause.replace('IS NULL', 'is None')
        conditions = conditions.replace('IS NOT NULL', 'is not None')
        for attr in attributes:
            conditions = conditions.replace(' %s ' % attr, ' doc["%s"] ')
        return conditions

    def _format_select_clause(self):
        select_clause = re.sub(r'ORDER BY.*', '', re.sub(r'.*SELECT', '', self.query)).strip()
        select_clause = re.sub(r'WHERE.*', '', re.sub(r'FROM.*', '', select_clause)).strip()
        select_attrs = select_clause.split(',')
        condition = '{'
        #handle aliases
        for attr_s in select_attrs:
            attr = attr_s.split()
            if re.match(r'COUNT\(.*\)', attr[0]):
                    attr[0] = re.sub(r'\)', '', re.sub(r'.*COUNT\(', '', attr[0])).strip()
                    self.aggr_fns['COUNT'] = {}
                    if attr[0].upper() == 'DISTINCT':
                        attr = attr[1:]
                        self.distict= True
                    self.aggr_fns['COUNT']['field'] = attr[0]
                    self.aggr_fns['COUNT']['alias'] = ('$1', attr[-1])[len(attr) > 1]
            elif attr[0].upper() == 'DISTINCT':
                attr = attr[1:]
                self.distict= True
            if len(attr) == 1:
                condition += '"%s" : doc["%s"],' % (attr[0], attr[0])
            elif len(attr) == 2:
                condition += '"%s" : doc["%s"],' % (attr[1], attr[0])
            elif len(attr) == 3 and ('as' in attr or 'AS' in attr):
                condition += '"%s" : doc["%s"],' % (attr[2], attr[0])
        condition += '}'
        return condition

    def _filter_full_set(self, select_clause, where_clause):
        if where_clause:
            result = [eval(select_clause) for doc in self.full_set if eval(where_clause)]
        else:
            result = [eval(select_clause) for doc in self.full_set]
        if self.distict:
            result = [dict(y) for y in set(tuple(x.items()) for x in result)]
        if self.aggr_fns:
            for fn_name, params in self.aggr_fns.iteritems():
                if fn_name == 'COUNT':
                    result = [{params['alias'] : len(result)}]
        return result

    def _order_results(self, result):
        order_clause = None
        if self.query.find('ORDER BY') != -1:
            order_clause = re.sub(r'LIMIT.*', '', re.sub(r'.*ORDER BY', '', self.query)).strip()
            order_clause = re.sub(r'OFFSET.*', '', order_clause).strip()
        key = None
        reverse = False
        if order_clause:
            condition = ""
            order_attrs = order_clause.split(',')
            for attr_s in order_attrs:
                attr = attr_s.split()
                if len(attr) == 1 or (len(attr) == 2 and attr[1].upper() == 'ASC'):
                    condition += 'doc["%s"],' % attr[0]
                elif len(attr) == 2 and attr[1].upper() == 'DESC':
                    condition += 'doc["%s"],' % attr[0]
                    reverse = True
            key = lambda doc: eval(condition)
        result = sorted(result, key=key, reverse=reverse)
        return result

    def _limit_and_offset(self, result):
        limit_clause = offset_clause = None
        if self.query.find('LIMIT') != -1:
            limit_clause = re.sub(r'OFFSET.*', '', re.sub(r'.*LIMIT', '', self.query)).strip()
        if self.query.find('OFFSET') != -1:
            offset_clause = re.sub(r'.*OFFSET', '', self.query).strip()
        if limit_clause:
            result = result[:int(limit_clause)]
        if offset_clause:
            result = result[int(limit_clause):]
        return result