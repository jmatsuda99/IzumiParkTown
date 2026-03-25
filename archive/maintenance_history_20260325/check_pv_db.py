import sqlite3

conn = sqlite3.connect("izumi_power.db")

print("tables =", conn.execute(
    "select name from sqlite_master where type='table' and name like 'pv_profile_%'"
).fetchall())

print("datasets =", conn.execute(
    "select count(*) from pv_profile_datasets"
).fetchone())

print("records =", conn.execute(
    "select count(*) from pv_profile_records"
).fetchone())

conn.close()
