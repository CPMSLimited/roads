from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("all_roads", "0039_alter_subsegment_end_lat_alter_subsegment_end_lon_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                """
                ALTER TABLE sub_segments
                DROP CONSTRAINT IF EXISTS sub_segments_segment_id_08b73431_fk_all_roads_segment_id;
                """,
                """
                ALTER TABLE sub_segments
                ADD CONSTRAINT sub_segments_segment_id_08b73431_fk_all_roads_segment_id
                FOREIGN KEY (segment_id)
                REFERENCES all_roads_segment (id)
                ON DELETE CASCADE
                DEFERRABLE INITIALLY DEFERRED;
                """,
            ],
            reverse_sql=[
                """
                ALTER TABLE sub_segments
                DROP CONSTRAINT IF EXISTS sub_segments_segment_id_08b73431_fk_all_roads_segment_id;
                """,
                """
                ALTER TABLE sub_segments
                ADD CONSTRAINT sub_segments_segment_id_08b73431_fk_all_roads_segment_id
                FOREIGN KEY (segment_id)
                REFERENCES all_roads_segment (id)
                DEFERRABLE INITIALLY DEFERRED;
                """,
            ],
        ),
    ]
