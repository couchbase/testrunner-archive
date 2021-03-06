from base_2i import BaseSecondaryIndexingTests
from couchbase_helper.query_definitions import QueryDefinition

class SecondaryIndexingStatsConfigTests(BaseSecondaryIndexingTests):

    def setUp(self):
        super(SecondaryIndexingStatsConfigTests, self).setUp()

    def tearDown(self):
        super(SecondaryIndexingStatsConfigTests, self).tearDown()

    def test_index_stats(self):
        """
        Tests index stats when indexes are created and dropped
        """
        #Create Index
        self.run_multi_operations(buckets = self.buckets, 
            query_definitions = self.query_definitions, 
            create_index = True, drop_index = False)
        #Check Index Stats
        index_map = self.get_index_stats()
        self.log.info(index_map)
        for query_definition in self.query_definitions:
            index_name = query_definition.index_name
            for bucket in self.buckets:
                bucket_name = bucket.name
                check_keys = ['items_count', 'total_scan_duration', 'num_docs_queued',
                 'num_requests', 'num_rows_returned', 'num_docs_queued',
                 'num_docs_pending','delete_bytes' ]
                map = self._create_stats_map(items_count = 2016)
                self.verify_index_stats(index_map, index_name, bucket_name, map, check_keys)
        #Drop Index
        self.run_multi_operations(buckets = self.buckets, 
            query_definitions = self.query_definitions, 
            create_index = False, drop_index = True)
        index_map = self.get_index_stats()
        # Fix for CBQE-3071
        #Only the indexes created by this test
        #are being removed
        for query_definition in self.query_definitions:
            index_name = query_definition.index_name
            for bucket in self.buckets:
                self.assertNotIn(index_name, index_map[bucket.name].keys(), 
                    "Index {ind} present in bucket {buc}".format(
                        ind=index_name,
                        buc=bucket.name))

    def test_get_index_settings(self):
        #Check Index Settings
        map = self.get_index_settings()
        for node in map.keys():
            val = map[node]
            gen = self._create_settings_map()
            for key in gen.keys():
                self.assertTrue(key in val.keys(), "{0} not in {1} ".format(key, val))

    def test_set_index_settings(self):
        #Check Index Settings
        map1 = self._set_settings_map()
        self.log.info(map1)
        self.set_index_settings(map1)
        map = self.get_index_settings()
        for node in map.keys():
            val = map[node]
            for key in map1.keys():
                self.assertTrue(key in val.keys(), "{0} not in {1} ".format(key, val))

    def _create_stats_map(self, items_count = 0, total_scan_duration = 0,
        delete_bytes = 0, scan_wait_duration = 0, insert_bytes = 0,
        num_rows_returned = 0, num_docs_indexed = 0, num_docs_pending = 0,
        scan_bytes_read = 0, get_bytes = 0, num_docs_queued = 0,num_requests = 0,
        disk_size = 0):
        map = {}
        map['items_count'] = items_count
        map['disk_size'] = disk_size
        map['items_count'] = items_count
        map['total_scan_duration'] = total_scan_duration
        map['delete_bytes'] = delete_bytes
        map['scan_wait_duration'] = scan_wait_duration
        map['insert_bytes'] = insert_bytes
        map['num_rows_returned'] = num_rows_returned
        map['num_docs_indexed'] = num_docs_indexed
        map['num_docs_pending'] = num_docs_pending
        map['scan_bytes_read'] = scan_bytes_read
        map['get_bytes'] = get_bytes
        map['num_docs_queued'] = num_docs_queued
        map['num_requests'] = num_requests
        return map

    def _create_settings_map(self):
        map = { "indexer.settings.recovery.max_rollbacks" : 5,
        "indexer.settings.bufferPoolBlockSize" : 16384,
        "indexer.settings.max_cpu_percent" : 400,
        "queryport.client.settings.poolOverflow" : 30,
        "indexer.settings.memProfile" : False,
        "indexer.settings.statsLogDumpInterval" : 60,
        "indexer.settings.persisted_snapshot.interval" : 5000,
        "indexer.settings.inmemory_snapshot.interval" : 200,
        "indexer.settings.compaction.check_period" : 30,
        "indexer.settings.largeSnapshotThreshold" : 200,
        "indexer.settings.log_level" : "debug",
        "indexer.settings.scan_timeout" : 120000,
        "indexer.settings.maxVbQueueLength" : 0,
        "indexer.settings.send_buffer_size" : 1024,
        "indexer.settings.compaction.min_size" : 1048576,
        "indexer.settings.cpuProfFname" : "",
        "indexer.settings.memory_quota" : 268435456,
        "indexer.settings.memProfFname" : "",
        "projector.settings.log_level" : "debug",
        "queryport.client.settings.poolSize" : 1000,
        "indexer.settings.max_writer_lock_prob" : 20,
        "indexer.settings.compaction.interval" : "00:00,00:00",
        "indexer.settings.cpuProfile" : False,
        "indexer.settings.compaction.min_frag" : 30,
        "indexer.settings.sliceBufSize" : 50000,
        "indexer.settings.wal_size" : 4096,
        "indexer.settings.fast_flush_mode" : True,
        "indexer.settings.smallSnapshotThreshold" : 30,
        "indexer.settings.persisted_snapshot_init_build.interval": 5000
}
        return map

    def _set_settings_map(self):
        map = { "indexer.settings.recovery.max_rollbacks" : 4,
        "indexer.settings.bufferPoolBlockSize" : 16384,
        "indexer.settings.max_cpu_percent" : 400, 
        "indexer.settings.memProfile" : False,
        "indexer.settings.statsLogDumpInterval" : 60,
        "indexer.settings.persisted_snapshot.interval" : 5000,
        "indexer.settings.inmemory_snapshot.interval" : 200,
        "indexer.settings.compaction.check_period" : 31,
        "indexer.settings.largeSnapshotThreshold" : 200,
        "indexer.settings.log_level" : "debug",
        "indexer.settings.scan_timeout" : 120000,
        "indexer.settings.maxVbQueueLength" : 0,
        "indexer.settings.send_buffer_size" : 1024,
        "indexer.settings.compaction.min_size" : 1048576,
        "indexer.settings.cpuProfFname" : "",
        "indexer.settings.memory_quota" : 268435456,
        "indexer.settings.memProfFname" : "",
        "indexer.settings.persisted_snapshot_init_build.interval": 5000,
        "indexer.settings.max_writer_lock_prob" : 20,
        "indexer.settings.compaction.interval" : "00:00,00:00",
        "indexer.settings.cpuProfile" : False,
        "indexer.settings.compaction.min_frag" : 31,
        "indexer.settings.sliceBufSize" : 50000,
        "indexer.settings.wal_size" : 4096,
        "indexer.settings.fast_flush_mode" : True,
        "indexer.settings.smallSnapshotThreshold" : 30,
        "projector.settings.log_level" : "debug",
        "queryport.client.settings.poolSize" : 1000,
        "queryport.client.settings.poolOverflow" : 30
}
        return map