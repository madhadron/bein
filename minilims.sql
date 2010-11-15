CREATE TABLE execution ( 
     id integer primary key, 
     started_at integer not null, 
     finished_at integer default null,
     working_directory text not null, 
     description text not null default '' 
);

CREATE TABLE program (
       pos integer,
       execution integer references execution(id),
       pid integer not null,
       stdin text default null,
       return_code integer not null,
       stdout text default null,
       stderr text default null,
       primary key (pos,execution)
);

CREATE TABLE argument (
       pos integer,
       program integer references program(pos),
       execution integer references program(execution),
       argument text not null,
       primary key (pos,program,execution)
);

CREATE TABLE file ( 
       id integer primary key autoincrement, 
       external_name text, 
       repository_name text,
       created timestamp default current_timestamp, 
       description text not null default '',
       origin text not null default 'execution', 
       origin_value integer default null
);




CREATE TABLE schema_version ( schema_version integer primary key );
CREATE VIEW execution_dependencies as select execution, argument as file FROM command_args WHERE type = 'file';
CREATE VIEW execution_immutability AS SELECT ex.id AS id, ex.started_at AS started_at, ex.finished_at AS finished_at, ex.temp_dir AS temp_dir, ex.description AS description, MAX(imm.immutable) > 0 AND max(imm.immutable) IS NOT NULL AS immutable FROM execution AS ex LEFT JOIN file_immutability AS imm ON imm.origin = 'execution' AND imm.origin_value = ex.id GROUP BY ex.id;
CREATE VIEW file_immutability AS SELECT file.id AS id, file.external_name AS ext        ernal_name, file.repository_name AS repository_name, file.created AS created, file.description AS description, file.origin AS origin, file.origin_value AS origin_value, execution_dependencies.execution is not null AS immutable FROM file LEFT JOIN execution_dependencies ON file.id = execution_dependencies.file;

CREATE TRIGGER delete_file AFTER DELETE ON file FOR EACH ROW BEGIN 
SELECT deletefile(OLD.repository_name);

CREATE TRIGGER prevent_command_arg_delete BEFORE DELETE ON command_args FOR EACH ROW WHEN (SELECT immutable FROM execution_immutability WHERE id = OLD.execution) = 1 BEGIN SELECT RAISE(FAIL, 'Execution is immutable; cannot delete command argument.'); END;
CREATE TRIGGER prevent_command_args_update BEFORE UPDATE ON command_args FOR EACH ROW WHEN (SELECT immutable FROM execution_immutability WHERE id = OLD.execution) = 1 BEGIN SELECT RAISE(FAIL, 'Execution is immutable; cannot update command arguments.'); END;
CREATE TRIGGER prevent_command_delete BEFORE DELETE ON command FOR EACH ROW WHEN (SELECT immutable FROM execution_immutability WHERE id = OLD.execution) = 1 BEGIN SELECT RAISE(FAIL, 'Execution is immutable; cannot delete command.'); END;
CREATE TRIGGER prevent_command_update BEFORE UPDATE ON command FOR EACH ROW WHEN (SELECT immutable FROM execution_immutability WHERE id = OLD.execution) = 1 BEGIN SELECT RAISE(FAIL, 'Execution is immutable; cannot update commands.'); END;
CREATE TRIGGER prevent_execution_delete BEFORE DELETE ON execution FOR EACH ROW WHEN (SELECT immutable FROM execution_immutability WHERE id = OLD.id) = 1 BEGIN SELECT RAISE(FAIL, 'Execution is immutable; cannot delete.'); END;
CREATE TRIGGER prevent_execution_update BEFORE UPDATE ON execution FOR EACH ROW WHEN (SELECT immutable FROM execution_immutability WHERE id = OLD.id) = 1 AND (OLD.id != NEW.id OR OLD.started_at != NEW.started_at OR OLD.finished_at != NEW.finished_at OR OLD.temp_dir != NEW.temp_dir) BEGIN SELECT RAISE(FAIL, 'Execution is immutable; cannot update anything but description.'); END;
CREATE TRIGGER prevent_file_delete BEFORE DELETE ON file FOR EACH ROW WHEN (SELECT immutable FROM file_immutability WHERE id = old.id) = 1 BEGIN SELECT RAISE(FAIL, 'File is immutable; cannot delete.'); 
END;
CREATE TRIGGER prevent_file_update BEFORE UPDATE on file FOR EACH ROW WHEN (SELECT immutable FROM file_immutability WHERE id = old.id) = 1 AND (OLD.id != NEW.id OR OLD.external_name != NEW.external_name OR OLD.repository_name != NEW.repository_name OR OLD.created != NEW.created OR OLD.origin != NEW.origin OR OLD.origin_value != NEW.origin_value) BEGIN SELECT RAISE(FAIL, 'File is immutable; cannot update except description.'); END;
