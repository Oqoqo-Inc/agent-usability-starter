CREATE DATABASE fixture;
CREATE TABLE fixture.orders (
  order_id String,
  tenant String,
  status String,
  ordered_on Date,
  amount_cents UInt32
) ENGINE = MergeTree ORDER BY order_id;

INSERT INTO fixture.orders
SELECT
  hex(MD5(concat('oqoqo-order-export-nov16-v1:',toString(number)))),
  if(number % 4 = 0, 'cedar', 'orchid'),
  if(number % 5 = 0, 'void', 'paid'),
  if(number % 7 = 0, toDate('2026-02-01'), addDays(toDate('2026-01-01'), number % 31)),
  1200 + (number * 7919) % 100003
FROM numbers(240);

CREATE USER bench_reader IDENTIFIED WITH no_password SETTINGS readonly=1;
GRANT SELECT ON fixture.orders TO bench_reader;
