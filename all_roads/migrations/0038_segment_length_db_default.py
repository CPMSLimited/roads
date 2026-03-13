from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0037_route_start_end_point"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
DO $$
BEGIN
    -- Legacy schema path: physical column is "Length"
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'all_roads_segment'
          AND column_name = 'Length'
    ) THEN
        EXECUTE 'UPDATE all_roads_segment SET "Length" = 0 WHERE "Length" IS NULL';
        EXECUTE 'ALTER TABLE all_roads_segment ALTER COLUMN "Length" SET DEFAULT 0';
    END IF;

    -- Standard Django schema path: physical column is distance
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'all_roads_segment'
          AND column_name = 'distance'
    ) THEN
        EXECUTE 'UPDATE all_roads_segment SET distance = 0 WHERE distance IS NULL';
        EXECUTE 'ALTER TABLE all_roads_segment ALTER COLUMN distance SET DEFAULT 0';
    END IF;
END
$$;
""",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
