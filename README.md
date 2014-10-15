When using a database the size of OpenStreetMap, database speed is crucial. A sequential scan through the database to search for items is no longer an option, indexes are important. There are several types of database layouts possible and there are several types of indexes.

This code / document shall help in looking for the best database layout resp. index type.

== Database Layouts ==
=== Classic "relational" layout ===
The classic "relational" layout is available via Osmosis, the 'pgsimple' layout. As the keys of tags are not limited (classic n-m relationship), the tags are transferred to a separate table, e.g. nodes and node_tags.

==== Table 'nodes' ====

column | type
-------|------
id     | bigint
geom   | geometry

==== Table 'node_tags' ====

column  | type   | description
--------|--------|-------------
node_id | bigint | node_id is a foreign key to nodes.id.
k       | text
v       | text

==== Typical query ====
All objects with a name and tags amenity=bar or amenity=restaurant in a specified bounding box. For each object we want id, name, value of the tags amenity and cuisine, and finally the geometry:
```sql
select
  nodes.id,
  node_tags1.v as name,
  node_tags2.v as amenity,
  (select v from node_tags where node_id=id and k='cuisine') as cuisine,
  nodes.geom
from
  nodes join
  node_tags node_tags1 on nodes.id=node_tags1.id join
  node_tags node_tags2 on nodes.id=node_tags2.id
where
  nodes.geom && BBOX and
  node_tags1.k='name' and
  node_tags2.k='amenity' and node_tags2.v in ('bar', 'restaurant');
```

==== Conclusion ===
As you can see, queries are rather complex. Also, you have to do a lot of joins with which are rather expensive.

=== Column layout ===
This is the most common layout when you import your database with osm2pgsql or imposm. From a specified list of tags for each of the database tables (those containing OpenStreetMap objects) a column is created:

==== Table 'nodes' ====

column  | type
--------|------
id      | bigint
name    | text
highway | text
amenity | text
cuisine | text
ref     | text
geom    | geometry

==== Typical query ====
All objects with a name and tags amenity=bar or amenity=restaurant in a specified bounding box. For each object we want id, name, value of the tags amenity and cuisine, and finally the geometry:
```sql
select
  id,
  name,
  amenity,
  cusine,
  geom
from
  nodes
where
  geom && BBOX and
  name is not null and
  amenity in ('restaurant', 'bar');
```

==== Conclusion ===
The column layout is easy to use. The main disadvantage is, that you have to know all tags you are interested in prior to import - all other tags are discarded.

=== HStore layout ===
PostgreSQL has a powerful datatype called 'hstore'. It's a key/value storage with (more or less) unlimited size. Keys and values are always strings. An example hstore looks like this: '"name"=>"Some bar", "amenity"=>"bar", "cuisine"=>"regional"'.

==== Table 'nodes' ====
column  | type
--------|------
id      | bigint
tags    | hstore
geom    | geometry

==== Typical query ====
All objects with a name and tags amenity=bar or amenity=restaurant in a specified bounding box. For each object we want id, name, value of the tags amenity and cuisine, and finally the geometry:
```sql
select
  id,
  tags->'name' as name,
  tags->'amenity' as amenity,
  tags->'cusine' as cuisine,
  geom
from
  nodes
where
  geom && BBOX and
  tags ? 'name' and
  (tags @> 'amenity=>restaurant' or tags @> 'amenity=>bar');
```

==== Conclusion ===
The hstore layout is very powerful as it can store arbitrary OpenStreetMap objects. The main disadvantage is the more complex syntax for querying the database.

=== Mixed layout ===
osm2pgsql can additionally populate a hstore type "tags" column, either with the tags which do not have a specified database column or all tags of the feature.

==== Table 'nodes' ====

column  | type
--------|------
id      | bigint
name    | text
highway | text
amenity | text
ref     | text
tags    | hstore
geom    | geometry

==== Typical query ====
All objects with a name and tags amenity=bar or amenity=restaurant in a specified bounding box. For each object we want id, name, value of the tags amenity and cuisine, and finally the geometry:
```sql
select
  id,
  name,
  amenity,
  tags->'cusine' as cuisine,
  geom
from
  nodes
where
  geom && BBOX and
  name is not null and
  amenity in ('restaurant', 'bar');
```

==== Conclusion ===
The mixed layout seems quite perfect as for most tags the usual columns can be used and for additional tags you can still access the tags column.
