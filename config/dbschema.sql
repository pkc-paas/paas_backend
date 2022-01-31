DROP TABLE IF EXISTS users;
CREATE TABLE users(
	username VARCHAR(50) NOT NULL PRIMARY KEY,
	email VARCHAR(100) NULL,
	role VARCHAR(32) NULL,
	token VARCHAR(100) NULL,
	last_login DATETIME NULL,
	pwd VARCHAR(100) NULL,
	fullname VARCHAR(50) NULL,
	status VARCHAR(32) NULL,
	remarks VARCHAR(255) NULL,
	created_on DATETIME NULL,
	created_by VARCHAR(32) NULL,
	last_pw_change DATE NULL
);
CREATE INDEX users_i1 ON users (token);
CREATE INDEX users_i2 ON users (role);


DROP TABLE IF EXISTS saplings;
CREATE TABLE saplings(
	id VARCHAR(36) NOT NULL PRIMARY KEY,
	lat DECIMAL(9,6) NULL,
	lon DECIMAL(9,6) NULL,
	name VARCHAR(100) NULL,
	`group` VARCHAR(32) NULL,
	local_name VARCHAR(100) NULL,
	botanical_name VARCHAR(100) NULL,
	planted_date DATE NULL,
	data_collection_date DATE NULL
	status VARCHAR(50) NULL,
	description TEXT NULL,
	details TEXT NULL,
	first_photos VARCHAR(500) NULL,
	confirmed BOOLEAN NULL,
	created_on DATETIME NULL,
	created_by VARCHAR(32) NULL,
	modified_on DATETIME NULL,
	modified_by VARCHAR(32) NULL,
	CONSTRAINT saplings_c1 UNIQUE (lat, lon)
);
CREATE INDEX saplings_i1 ON saplings (planted_date);
CREATE INDEX saplings_i2 ON saplings (status);
CREATE INDEX saplings_i3 ON saplings (confirmed);
CREATE INDEX saplings_i4 ON saplings (`group`);
CREATE INDEX saplings_i5 ON saplings (name);


DROP TABLE IF EXISTS adoptions;
CREATE TABLE adoptions(
	id VARCHAR(36) NOT NULL PRIMARY KEY,
	username VARCHAR(32) NULL,
	sapling_id VARCHAR(36) NULL,
	adopted_name VARCHAR(32) NULL,
	comments VARCHAR(255) NULL,
	status VARCHAR(32) NULL,
	approver VARCHAR(32) NULL,
	application_date DATE NULL,
	approval_date DATE NULL,
	created_on DATETIME NULL,
	created_by VARCHAR(32) NULL,
	modified_on DATETIME NULL,
	modified_by VARCHAR(32) NULL,
	CONSTRAINT adoptions_c1 UNIQUE (username, sapling_id)
);
CREATE INDEX adoptions_i1 ON adoptions (username);
CREATE INDEX adoptions_i2 ON adoptions (sapling_id);
CREATE INDEX adoptions_i3 ON adoptions (status);
CREATE INDEX adoptions_i4 ON adoptions (approver);
CREATE INDEX adoptions_i5 ON adoptions (application_date);
CREATE INDEX adoptions_i6 ON adoptions (approval_date);


DROP TABLE IF EXISTS observations;
CREATE TABLE observations(
	id VARCHAR(36) NOT NULL PRIMARY KEY,
	sapling_id VARCHAR(36) NULL,
	photo_id VARCHAR(200) NULL,
	observation_date DATE NULL,
	growth_status VARCHAR(200) NULL,
	health_status VARCHAR(200) NULL,
	description VARCHAR(500) NULL,
	confirmed BOOLEAN NULL,
	created_on DATETIME NULL,
	created_by VARCHAR(32) NULL,
	modified_on DATETIME NULL,
	modified_by VARCHAR(32) NULL
);
CREATE INDEX observations_i1 ON observations (sapling_id);
CREATE INDEX observations_i2 ON observations (observation_date);
CREATE INDEX observations_i3 ON observations (confirmed);

