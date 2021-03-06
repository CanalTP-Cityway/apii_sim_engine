BEGIN;

INSERT INTO mis (name, comment, api_url, api_key, start_date, end_date, shape,
                 geographic_position_compliant, multiple_starts_and_arrivals) VALUES
    ('mis1', 'comment1', 'mis1_url', '', DATE '2007-05-16', 
     DATE '2016-05-16', NULL, TRUE, 0),
    ('mis2', 'comment2', 'mis2_url', '', DATE '2008-02-19', 
     DATE '2016-04-16', st_geogfromtext('SRID=4326;MULTIPOLYGON(((1.5 -1.5, 1.5 1.5, -1.5 1.5, -1.5 -1.5, 1.5 -1.5)))'), TRUE, 0),
    ('mis3', 'comment3', 'mis3_url', '', DATE '2008-02-19', 
     DATE '2016-04-16', NULL, FALSE, 1),
    ('mis4', 'comment4', 'mis4_url', '', DATE '2008-02-19', 
     DATE '2016-04-16', NULL, TRUE, 1),
    ('mis5', 'comment5', 'mis5_url', '', DATE '2008-02-19', 
     DATE '2016-04-16', NULL, TRUE, 1),
    ('mis6', 'comment6', 'mis6_url', '', DATE '2008-02-19', 
     DATE '2016-04-16', NULL, TRUE, 1);

INSERT INTO stop (code, mis_id, name, lat, long) VALUES
    ('stop_code10', 1, '', 1, 1),
    ('stop_code20', 2, '', 2, 2),
    ('stop_code30', 3, '', 3, 3),
    ('stop_code40', 4, '', 4, 4),
    ('stop_code11', 1, '', 0, 0),
    ('stop_code21', 2, '', 1.4, 1.4),
    ('stop_code31', 3, '', 0, 0),
    ('stop_code41', 4, '', 8, 8),
    ('stop_code12', 1, '', 0, 0),
    ('stop_code22', 2, '', 0, 0),
    ('stop_code32', 3, '', 0, 0),
    ('stop_code42', 4, '', 8, 8),
    ('stop_code13', 1, '', 0, 0),
    ('stop_code23', 2, '', 0, 0),
    ('stop_code33', 3, '', 0, 0),
    ('stop_code43', 4, '', 8, 8),
    ('stop_code60', 6, '', 6, 6);

INSERT INTO transfer (stop1_id, stop2_id, distance, duration, active, modification_state) VALUES
    (1, 2, 100, 10, TRUE, 'auto'),
    (6, 3, 100, 10, TRUE, 'auto'),
    (10, 3, 100, 10, TRUE, 'auto'),
    (14, 3, 100, 20, TRUE, 'auto'),
    (7, 4, 100, 10, TRUE, 'auto'),
    (11, 4, 100, 10, TRUE, 'auto'),
    (1, 12, 100, 30, TRUE, 'auto'),
    (3, 17, 100, 10, FALSE, 'auto');

INSERT INTO mis_connection (mis1_id, mis2_id, start_date, end_date) VALUES
    (1, 2, 
     (SELECT GREATEST((SELECT start_date from mis where id=1), (SELECT start_date from mis where id=2))), 
     (SELECT LEAST((SELECT end_date from mis where id=1), (SELECT end_date from mis where id=2)))),
    (2, 3,
     (SELECT GREATEST((SELECT start_date from mis where id=2), (SELECT start_date from mis where id=3))), 
     (SELECT LEAST((SELECT end_date from mis where id=2), (SELECT end_date from mis where id=3)))),
    (3, 4, 
     (SELECT GREATEST((SELECT start_date from mis where id=3), (SELECT start_date from mis where id=4))), 
     (SELECT LEAST((SELECT end_date from mis where id=3), (SELECT end_date from mis where id=4)))),
    (1, 4, 
     (SELECT GREATEST((SELECT start_date from mis where id=1), (SELECT start_date from mis where id=4))), 
     (SELECT LEAST((SELECT end_date from mis where id=1), (SELECT end_date from mis where id=4))));


INSERT INTO mode (code) VALUES
    ('bus'),
    ('tram'),
    ('funicular');

INSERT INTO mis_mode (mis_id, mode_id) VALUES
    (1,1),
    (2,1),
    (4,1),
    (1,2),
    (2,2),
    (3,2),
    (3,3),
    (5,1),
    (5,2),
    (5,3);

COMMIT;
\q
