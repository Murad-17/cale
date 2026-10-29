"""Statistics use persisted records, calendar boundaries and no sample values."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from storage import Store
from usage_stats import statistics


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)
        self.now = datetime(2026,10,22,12).timestamp()

    def tearDown(self):
        self.temp.cleanup()

    def message(self, text, days=0, source='companion', sender='user'):
        created = (datetime.fromtimestamp(self.now)-timedelta(days=days)).timestamp()
        with self.store.connection() as db:
            db.execute('INSERT INTO messages(sender,text,extras,created,thread_id) VALUES (?,?,?,?,?)',
                       (sender, text, json.dumps({'source':source,'private':'fixture-sensitive-text'}), created, 'saved-thread'))

    def stats(self, period):
        with patch('usage_stats.time.time', return_value=self.now):
            return statistics(self.store, period)

    def test_actual_counts_filters_sources_and_no_transcripts(self):
        self.message('Salam ORION')
        self.message('Bir yeni ideya',source='ui')
        self.message('Təhlil et bunu',days=3,source='companion_voice')
        self.message('Keçən həftə plan',days=15)
        self.message('Köhnə tarixçə',days=45)
        self.message('Bu cavabı sayma',sender='orion')
        self.message('Gələcək sətri sayma',days=-1)
        week,month,all_time = (self.stats(p) for p in ('week','month','all'))
        self.assertEqual((week['words'],month['words'],all_time['words']),(8,11,13))
        self.assertEqual((week['messages'],month['messages'],all_time['messages']),(3,4,5))
        self.assertEqual(len(week['series']),7)
        self.assertEqual(len(month['series']),30)
        self.assertEqual(sum(d['words'] for d in month['series']),month['words'])
        self.assertEqual(week['active_days'],2)
        self.assertEqual({s['id']:s['count'] for s in week['sources']},{'companion':1,'dashboard':1,'voice':1})
        self.assertIsNone(week['average_seconds'])
        self.assertNotIn('Salam',json.dumps(all_time))
        self.assertNotIn('fixture-sensitive-text',json.dumps(all_time))
        self.assertEqual(len(self.store.messages()),7)  # Read-only; nothing discarded.

    def test_api_latency_and_throughput_are_derived_from_real_usage(self):
        with self.store.connection() as db:
            db.executemany('INSERT INTO usage(provider,model,input_tokens,output_tokens,seconds,created) VALUES (?,?,?,?,?,?)',
                           [('fixture','model',10,100,2,self.now-60),('fixture','model',20,60,6,self.now-120),
                            ('fixture','old',10,999,9,self.now-90*86400)])
        data=self.stats('week')
        self.assertEqual(data['api_calls'],2)
        self.assertEqual(data['average_seconds'],4)
        self.assertEqual(data['tokens_per_second'],20)
        self.assertEqual(self.stats('all')['api_calls'],3)  # Usage can predate the first saved message.

    def test_local_midnight_is_inclusive_and_empty_ranges_have_honest_zeroes(self):
        start=datetime(2026,10,16)
        with self.store.connection() as db:
            for stamp in [start.timestamp(),start.timestamp()-1]:
                db.execute("INSERT INTO messages(sender,text,extras,created) VALUES ('user','bir söz','{}',?)",(stamp,))
        self.assertEqual(self.stats('week')['words'],2)
        self.assertEqual(self.stats('month')['words'],4)
        empty=statistics(Store(self.temp.name+'/empty'),'week')
        self.assertEqual(empty['messages'],0)
        self.assertEqual(empty['sources'],[])
        self.assertIsNone(empty['tokens_per_second'])
        self.assertTrue(all(row['words']==0 for row in empty['series']))
        with self.assertRaises(ValueError):self.stats('invalid')

    def test_all_time_stays_bounded_and_preserves_every_word(self):
        self.message('çox köhnə qeyd',days=365*20)
        self.message('indiki qeyd')
        data=self.stats('all')
        self.assertEqual(data['bucket'],'year')
        self.assertLessEqual(len(data['series']),22)
        self.assertEqual(sum(d['words'] for d in data['series']),5)


if __name__=='__main__':unittest.main()
