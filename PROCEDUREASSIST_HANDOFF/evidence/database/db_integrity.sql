-- Read-only integrity checks (27 Oct 2026). Every query only reads.
SELECT 'pages' AS check, count(*)::text AS value FROM procedures
UNION ALL SELECT 'chunks', count(*)::text FROM procedure_chunks
UNION ALL SELECT 'duplicate source_url', count(*)::text FROM (SELECT source_url FROM procedures GROUP BY source_url HAVING count(*) > 1) d
UNION ALL SELECT 'orphaned chunks', count(*)::text FROM procedure_chunks c LEFT JOIN procedures p ON p.id = c.procedure_id WHERE p.id IS NULL
UNION ALL SELECT 'chunks without embedding', count(*)::text FROM procedure_chunks WHERE embedding IS NULL
UNION ALL SELECT 'embedding dimensions', string_agg(DISTINCT vector_dims(embedding)::text, ',') FROM procedure_chunks
UNION ALL SELECT 'pages without chunks', count(*)::text FROM procedures p WHERE NOT EXISTS (SELECT 1 FROM procedure_chunks c WHERE c.procedure_id = p.id)
UNION ALL SELECT 'chunk numbering gaps', count(*)::text FROM (SELECT procedure_id FROM procedure_chunks GROUP BY procedure_id
        HAVING min(chunk_index) <> 0 OR max(chunk_index) <> count(*) - 1 OR count(DISTINCT chunk_index) <> count(*)) g
UNION ALL SELECT 'chunk foreign key on delete', string_agg(rc.delete_rule, ',') FROM information_schema.referential_constraints rc
        JOIN information_schema.table_constraints tc ON tc.constraint_name = rc.constraint_name WHERE tc.table_name = 'procedure_chunks'
UNION ALL SELECT 'unique constraint on source_url', count(*)::text FROM pg_indexes WHERE tablename = 'procedures' AND indexdef ILIKE '%UNIQUE%source_url%';
