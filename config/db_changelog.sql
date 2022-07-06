-- DB changes recording


-- 2022-06-05

ALTER TABLE sessions ADD ip VARCHAR(20) NULL;

ALTER TABLE users ADD creator_ip VARCHAR(20) NULL;

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


-- done in local DB, server DB

----------------

-- 2022-06-19

DROP TABLE IF EXISTS events;
CREATE TABLE events(
	evid VARCHAR(10) NOT NULL PRIMARY KEY,
	start_date DATE NULL,
	end_date DATE NULL,
	start_time TIME NULL,
	end_time TIME NULL,
	title VARCHAR(100) NULL,
	description TEXT NULL,
	files VARCHAR(500) NULL,
	tags VARCHAR(100) NULL,
	disabled BIT DEFAULT 0 NOT NULL,
	highlight BIT DEFAULT 0 NOT NULL,
	created_by VARCHAR(50) NULL,
	created_on DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	modified_by VARCHAR(50) NULL,
	modified_on DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- done in local DB, server DB

-- 2022-06-21
ALTER TABLE events ADD join_link VARCHAR(500) NULL;
ALTER TABLE events ADD location_addr VARCHAR(200) NULL;
ALTER TABLE events ADD lat DECIMAL(9,6) NULL;
ALTER TABLE events ADD lon DECIMAL(9,6) NULL;


-- done in local, server

