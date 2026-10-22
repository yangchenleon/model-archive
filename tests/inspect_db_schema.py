import os
import sys
from pathlib import Path

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://model_archive:model_archive_dev@127.0.0.1:15432/model_archive"

sys.path.insert(0, str(Path("backend").resolve()))

from sqlalchemy import inspect
from app.db import engine

inspector = inspect(engine)

print("=== Tables in Database ===")
tables = inspector.get_table_names()
print(tables)

for table_name in tables:
    print(f"\n=== Columns in table '{table_name}' ===")
    columns = inspector.get_columns(table_name)
    for col in columns:
        print(f"  {col['name']:20s} | {str(col['type']):20s} | nullable={col['nullable']} | default={col.get('default')}")

    pk = inspector.get_pk_constraint(table_name)
    print(f"  Primary Key: {pk}")

    fks = inspector.get_foreign_keys(table_name)
    if fks:
        print(f"  Foreign Keys: {fks}")

    indexes = inspector.get_indexes(table_name)
    if indexes:
        print("  Indexes:")
        for idx in indexes:
            print(f"    {idx['name']}: cols={idx['column_names']}, unique={idx['unique']}")

    uniques = inspector.get_unique_constraints(table_name)
    if uniques:
        print("  Unique Constraints:")
        for u in uniques:
            print(f"    {u['name']}: cols={u['column_names']}")
