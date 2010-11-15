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

CREATE TABLE execution_use (
       execution integer references execution(id),
       file integer references file(id)
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

CREATE TRIGGER prevent_repository_name_change BEFORE UPDATE ON file
FOR EACH ROW WHEN (OLD.repository_name != NEW.repository_name) BEGIN
     SELECT RAISE(FAIL, 'Cannot change the repository name of a file.');
END;

CREATE VIEW file_immutability AS 
SELECT file as id, count(execution) > 0 as immutable from execution_use group by file;

CREATE VIEW execution_outputs AS
select execution.id as execution, file.id as file 
from execution left join file 
on execution.id = file.origin_value
and file.origin='execution';


CREATE VIEW execution_immutability AS
SELECT eo.execution as id, ifnull(max(fi.immutable),0) from
execution_outputs as eo left join file_immutability as fi
on eo.file = fi.immutable
group by id;

CREATE TRIGGER prevent_file_delete BEFORE DELETE ON file 
FOR EACH ROW WHEN 
    (SELECT immutable FROM file_immutability WHERE id = OLD.id) = 1
BEGIN
    SELECT RAISE(FAIL, 'File is immutable; cannot delete it.'); 
END;

CREATE TRIGGER prevent_argument_delete BEFORE DELETE ON argument
FOR EACH ROW WHEN 
    (SELECT immutable FROM execution_immutability WHERE id = OLD.execution) = 1 
BEGIN 
    SELECT RAISE(FAIL, 'Execution is immutable; cannot delete argument.'); 
END;	   

CREATE TRIGGER prevent_argument_update BEFORE UPDATE ON argument
FOR EACH ROW WHEN
    (SELECT immutable FROM execution_immutability WHERE id = OLD.execution) = 1 
BEGIN
    SELECT RAISE(FAIL, 'Execution is immutable; cannot update command arguments.'); 
END;

CREATE TRIGGER prevent_command_delete BEFORE DELETE ON program
FOR EACH ROW WHEN 
    (SELECT immutable FROM execution_immutability WHERE id = OLD.execution) = 1 
BEGIN
    SELECT RAISE(FAIL, 'Execution is immutable; cannot delete command.'); 
END;

CREATE TRIGGER prevent_command_update BEFORE UPDATE ON program
FOR EACH ROW WHEN 
    (SELECT immutable FROM execution_immutability WHERE id = OLD.execution) = 1
BEGIN
    SELECT RAISE(FAIL, 'Execution is immutable; cannot update commands.'); 
END;

CREATE TRIGGER prevent_execution_delete BEFORE DELETE ON execution 
FOR EACH ROW WHEN
    (SELECT immutable FROM execution_immutability WHERE id = OLD.id) = 1
BEGIN
    SELECT RAISE(FAIL, 'Execution is immutable; cannot delete.'); 
END;

CREATE TRIGGER prevent_execution_update BEFORE UPDATE ON execution
FOR EACH ROW WHEN
    (SELECT immutable FROM execution_immutability WHERE id = OLD.id) = 1 AND 
    (OLD.id != NEW.id OR OLD.started_at != NEW.started_at OR OLD.finished_at != NEW.finished_at
     OR OLD.temp_dir != NEW.temp_dir) 
BEGIN
    SELECT RAISE(FAIL, 'Execution is immutable; cannot update anything but description.'); 
END;

CREATE TRIGGER prevent_immutable_file_update BEFORE UPDATE on file 
FOR EACH ROW WHEN 
    (SELECT immutable FROM file_immutability WHERE id = old.id) = 1 AND 
    (OLD.id != NEW.id OR OLD.external_name != NEW.external_name OR 
     OLD.repository_name != NEW.repository_name OR 
     OLD.created != NEW.created OR OLD.origin != NEW.origin OR 
     OLD.origin_value != NEW.origin_value) 
BEGIN 
    SELECT RAISE(FAIL, 'File is immutable; cannot update except description.'); 
END;
