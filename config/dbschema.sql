DROP TABLE IF EXISTS users;
CREATE TABLE users(
	username VARCHAR(50) NOT NULL PRIMARY KEY,
	email VARCHAR(100) NULL,
	role VARCHAR(32) NULL,
	token VARCHAR(100) NULL,
	last_login DATETIME NULL,
	pwd VARCHAR(100) NULL,
	fullname VARCHAR(50) NULL,
	`status` VARCHAR(32) NULL,
	remarks VARCHAR(255) NULL,
	created_on DATETIME NULL,
	created_by VARCHAR(32) NULL,
	last_pw_change DATE NULL,
	referral_code VARCHAR(100) NULL,
	creator_ip VARCHAR(20) NULL
);
CREATE INDEX users_i1 ON users (token);
CREATE INDEX users_i2 ON users (role);


DROP TABLE IF EXISTS sessions;
CREATE TABLE sessions(
	token VARCHAR(50) NOT NULL PRIMARY KEY,
	username VARCHAR(50) NOT NULL,
	ip VARCHAR(20) NULL,
	created_on DATETIME NULL
);


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
	data_collection_date DATE NULL,
	`status` VARCHAR(50) NULL,
	`description` TEXT NULL,
	details TEXT NULL,
	first_photos VARCHAR(500) NULL,
	confirmed BOOLEAN NULL,
	created_on DATETIME NULL,
	created_by VARCHAR(32) NULL,
	modified_on DATETIME NULL,
	modified_by VARCHAR(32) NULL,
	height DECIMAL(6,2) NULL,
	canopy DECIMAL(6,2) NULL,
	girth_1m DECIMAL(6,2) NULL,
	CONSTRAINT saplings_c1 UNIQUE (lat, lon)
);
CREATE INDEX saplings_i1 ON saplings (planted_date);
CREATE INDEX saplings_i2 ON saplings (`status`);
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
	`status` VARCHAR(32) NULL,
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
CREATE INDEX adoptions_i3 ON adoptions (`status`);
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
	`description` VARCHAR(500) NULL,
	confirmed BOOLEAN NULL,
	created_on DATETIME NULL,
	created_by VARCHAR(32) NULL,
	modified_on DATETIME NULL,
	modified_by VARCHAR(32) NULL
);
CREATE INDEX observations_i1 ON observations (sapling_id);
CREATE INDEX observations_i2 ON observations (observation_date);
CREATE INDEX observations_i3 ON observations (confirmed);


DROP TABLE IF EXISTS species;
CREATE TABLE species(
	id VARCHAR(10) NOT NULL PRIMARY KEY,
	local_name VARCHAR(100) NULL,
	botanical_name VARCHAR(100) NULL,
	`description` VARCHAR(500) NULL,
	economic VARCHAR(100) NULL,
	phenology VARCHAR(100) NULL,
	flowering VARCHAR(100) NULL,
	fruiting VARCHAR(100) NULL,
	nativity VARCHAR(100) NULL,
	is_rare VARCHAR(1) NULL,
	created_on DATETIME NULL,
	created_by VARCHAR(32) NULL,
	modified_on DATETIME NULL,
	modified_by VARCHAR(32) NULL
);


DROP TABLE IF EXISTS referral_codes;
CREATE TABLE referral_codes(
	referral_code VARCHAR(100) NOT NULL PRIMARY KEY,
	valid_from DATETIME NULL,
	valid_upto DATETIME NULL,
	enabled BIT DEFAULT 0 NOT NULL,
	created_on DATETIME NULL,
	created_by VARCHAR(32) NULL,
	modified_on DATETIME NULL,
	modified_by VARCHAR(32) NULL
);


DROP TABLE IF EXISTS otps;
CREATE TABLE otps(
	txnid VARCHAR(100) NOT NULL PRIMARY KEY,
	otp SMALLINT NULL,
	purpose VARCHAR(32) NULL,
	created_for VARCHAR(32) NULL,
	created_on DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	ip VARCHAR(20) NULL,
	matched_on DATETIME NULL,
	validity SMALLINT NULL
);


DROP TABLE IF EXISTS events;
CREATE TABLE events(
	evid VARCHAR(10) NOT NULL PRIMARY KEY,
	start_date DATE NULL,
	end_date DATE NULL,
	start_time TIME NULL,
	end_time TIME NULL,
	title VARCHAR(100) NULL,
	`description` TEXT NULL,
	files VARCHAR(500) NULL,
	tags VARCHAR(100) NULL,
	disabled BIT DEFAULT 0 NOT NULL,
	highlight BIT DEFAULT 0 NOT NULL,
	created_by VARCHAR(50) NULL,
	created_on DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	modified_by VARCHAR(50) NULL,
	modified_on DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	join_link VARCHAR(500) NULL,
	location_addr VARCHAR(200) NULL,
	lat DECIMAL(9,6) NULL,
	lon DECIMAL(9,6) NULL
);

