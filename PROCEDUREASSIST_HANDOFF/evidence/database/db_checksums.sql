-- Content checksums used to prove a database is unchanged (run with psql -At -d <database> -f db_checksums.sql)
select 'pages', count(*) from procedures;
select 'chunks', count(*) from procedure_chunks;
select 'procedures_md5', md5(string_agg(id||name||coalesce(department,'')||coalesce(jurisdiction,'')||summary||source_url||source_text||structured_data::text, '|' order by id)) from procedures;
select 'chunks_md5', md5(string_agg(id||'/'||procedure_id||'/'||chunk_index||content||embedding::text, '|' order by id)) from procedure_chunks;
select 'orphan_chunks', count(*) from procedure_chunks c left join procedures p on p.id = c.procedure_id where p.id is null;
select 'embedding_dims', string_agg(distinct vector_dims(embedding)::text, ',') from procedure_chunks;
select 'pages_with_index_gaps', count(*) from (select procedure_id, count(*) n, max(chunk_index) m from procedure_chunks group by procedure_id) t where n <> m + 1;
