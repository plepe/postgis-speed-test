#!/usr/bin/python3
import getpass
import argparse
import postgresql
import datetime
import random

parser = argparse.ArgumentParser(description='Speed tests on a PostgreSQL/Postgis database table')

parser.add_argument('-d', '--database', dest='database',
    default=getpass.getuser(),
    help='Name of database (default: username)')

parser.add_argument('-u', '--user', dest='user',
    default=getpass.getuser(),
    help='User for database (default: username)')

parser.add_argument('-p', '--password', dest='password',
    default='PASSWORD',
    help='Password for database (default: PASSWORD)')

parser.add_argument('-H', '--host', dest='host',
    default='localhost',
    help='Host for database (default: localhost)')

parser.add_argument('-t', '--table', dest='table',
    help='Name of the database table to test')

parser.add_argument('-b', '--bbox', dest='bounding_box',
    help='Region in which tests are being performed')

parser.add_argument('-i', '--indexes', dest='indexes', nargs='+',
    help='List of indexes which should be tested.')

parser.add_argument('-D', '--drop', dest='drop_indexes', nargs='+',
    default=[],
    help='List of indexes which should (temporarily) be dropped to avoid accidential usage.')

parser.add_argument('-w', '--where', dest='where',
    help='Where selector, e.g. "tags @> \'amenity=>restaurant\'"')

def main():
    args = parser.parse_args()

    global conn
    conn = postgresql.open(
        host=args.host,
        password=args.password,
        database=args.database,
        user=args.user
    )

    timings = {
            i: test(args, i, [ 1024, 4096, 16384, 65536 ]) #16, 64, 256, 1024 ])
            for i in args.indexes
        }

    print(timings)

def test_timings(args, index, size, qry_plan):
    print("* Testing index {}, size {}".format(index, size))

    radius = size / 2.0

    plan = conn.prepare('select ST_XMin(bbox) xmin, ST_YMin(bbox) ymin, ST_XMax(bbox) xmax, ST_YMax(bbox) ymax from (select ST_Buffer(ST_Transform(SetSRID(MakeBox2D(ST_Point($1, $2), ST_Point($3, $4)), 4326), 900913), $5) bbox offset 0) t')
    bbox = [ float(b) for b in args.bounding_box.split(',') ]
    res = plan(bbox[0], bbox[1], bbox[2], bbox[3], -radius)
    bbox = res[0]

    time_start = datetime.datetime.now()
    passes = 0
    avg_item_count = 0
    while (datetime.datetime.now() - time_start).total_seconds() < 5.0:
        x = random.random() * (bbox[2] - bbox[0]) + bbox[0]
        y = random.random() * (bbox[3] - bbox[1]) + bbox[1]

        res = qry_plan(x - radius, y - radius, x + radius, y + radius)
        avg_item_count += res[0]['c']
        passes += 1

    duration = (datetime.datetime.now() - time_start).total_seconds()

    ret = {
        'duration': duration,
        'passes': passes,
        'avg_item_count': avg_item_count / passes,
        'time_per_pass': duration / passes,
    }

    for k, v in ret.items():
        print('  {}: {}'.format(k, v))

    return ret

def test(args, index, sizes):
    print("* Testing index {}, query plan:".format(index))
    plan = conn.prepare('begin');
    plan()

    where = ''
    if args.where:
        where = 'and (' + args.where + ')'

    for i in args.indexes:
        if i != index:
            plan = conn.prepare('drop index ' + i);
            plan()

    for i in args.drop_indexes:
        plan = conn.prepare('drop index ' + i);
        plan()

    plan = conn.prepare('explain select count(*) c from {} where way && SetSRID(MakeBox2D(ST_Point($1, $2), ST_Point($3, $4)), 900913) {}'.format(args.table, where))
    res = plan(0, 0, 0, 0)
    for r in res:
        print('  ' + r[0])

    qry_plan = conn.prepare('select count(*) c from {} where way && SetSRID(MakeBox2D(ST_Point($1, $2), ST_Point($3, $4)), 900913) {}'.format(args.table, where))

    ret = { s: test_timings(args, index, s, qry_plan) for s in sizes }

    plan = conn.prepare('rollback');
    plan()

    return ret

main()
