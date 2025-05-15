-- Database Data Backup generated on 2025-05-15 01:06:12.248928
-- This file contains INSERT statements for all data

-- Disable triggers during import
SET session_replication_role = 'replica';

-- Table: contact_property
-- 4 rows
INSERT INTO contact_property (contact_id, property_id, relationship_type, created_at) VALUES (1, 1, 'owner', '2025-05-12T01:20:38.876084');
INSERT INTO contact_property (contact_id, property_id, relationship_type, created_at) VALUES (2, 2, 'owner', '2025-05-12T01:21:31.707523');
INSERT INTO contact_property (contact_id, property_id, relationship_type, created_at) VALUES (3, 3, 'owner', '2025-05-12T01:25:05.629736');
INSERT INTO contact_property (contact_id, property_id, relationship_type, created_at) VALUES (6, 5, 'owner', '2025-05-14T03:14:31.189833');

-- Table: property
-- 4 rows
INSERT INTO property (id, unit_number, description, balance, entitlement, created_at) VALUES (1, 'Unit 1', NULL, -190.0, 1.0, '2025-05-12T01:19:21.414695');
INSERT INTO property (id, unit_number, description, balance, entitlement, created_at) VALUES (3, 'Unit 3', NULL, 0.0, 1.0, '2025-05-12T01:19:21.507015');
INSERT INTO property (id, unit_number, description, balance, entitlement, created_at) VALUES (2, 'Unit 2', NULL, -590.0, 1.0, '2025-05-12T01:19:21.465222');
INSERT INTO property (id, unit_number, description, balance, entitlement, created_at) VALUES (5, 'Unit 4', '', 0.0, 1.0, '2025-05-14T03:01:03.640485');

-- Table: billing_period
-- 1 rows
INSERT INTO billing_period (id, name, start_date, end_date, total_amount, description, created_at) VALUES (1, 'Q1 25-26', '2025-07-01T00:00:00', '2025-09-30T00:00:00', 1170.0, '', '2025-05-12T01:26:22.425458');

-- Table: payment
-- 6 rows
INSERT INTO payment (id, property_id, fee_id, amount, date, description, reference, reconciled, is_duplicate, confirmed, transaction_id, created_at) VALUES (1, 2, 2, 200.0, '2025-05-06T00:00:00', 'Keith Letcher', 'Keith Letcher', True, False, True, '76ca6ad78f21af46b1cf4a93261309f3', '2025-05-12T03:26:03.302411');
INSERT INTO payment (id, property_id, fee_id, amount, date, description, reference, reconciled, is_duplicate, confirmed, transaction_id, created_at) VALUES (2, 1, 1, 200.0, '2025-05-07T00:00:00', 'strata fee', 'strata fee', True, False, True, 'c6772799599dab2f75ac1ed476da0fb1', '2025-05-12T03:26:03.445670');
INSERT INTO payment (id, property_id, fee_id, amount, date, description, reference, reconciled, is_duplicate, confirmed, transaction_id, created_at) VALUES (3, 3, 3, 390.0, '2025-05-08T00:00:00', 'unit 3', 'unit 3', True, False, True, 'd6647cdad3184afd68952ee01df276aa', '2025-05-12T03:26:03.561697');
INSERT INTO payment (id, property_id, fee_id, amount, date, description, reference, reconciled, is_duplicate, confirmed, transaction_id, created_at) VALUES (4, 2, 4, 200.0, '2025-05-06T00:00:00', 'Keith Letcher', 'Keith Letcher', True, False, True, '76ca6ad78f21af46b1cf4a93261309f3', '2025-05-12T09:25:43.560356');
INSERT INTO payment (id, property_id, fee_id, amount, date, description, reference, reconciled, is_duplicate, confirmed, transaction_id, created_at) VALUES (5, 2, 4, 200.0, '2025-05-07T00:00:00', 'strata fee', 'strata fee', True, False, True, '76ca6ad78f21af46b1cf4a93261309f3', '2025-05-12T09:25:43.784183');
INSERT INTO payment (id, property_id, fee_id, amount, date, description, reference, reconciled, is_duplicate, confirmed, transaction_id, created_at) VALUES (6, NULL, NULL, -10000.0, '2025-05-12T00:00:00', 'Payment for expense: Strata Insurance', 'Insurance payment', True, False, True, 'a5f98e2a8901dec592f5563e2056b736', '2025-05-12T23:19:31.011370');

-- Table: strata_settings
-- 1 rows
INSERT INTO strata_settings (id, strata_name, address, admin_email, bank_account_name, bank_bsb, bank_account_number, created_at) VALUES (1, 'Strata Corporation', '123 Main Street', 'vaughan00@gmail.com', 'NAB', '445448', '55677888', '2025-05-14T01:07:14.788097');

-- Table: fee
-- 5 rows
INSERT INTO fee (id, property_id, amount, date, description, period, paid, created_at, fee_type, due_date, paid_amount) VALUES (2, 2, 390.0, '2025-07-01T00:00:00', 'Strata fee for Q1 25-26', 'Q1 25-26', True, '2025-05-12T01:26:22.625079', 'billing_period', '2025-07-31T00:00:00', 200.0);
INSERT INTO fee (id, property_id, amount, date, description, period, paid, created_at, fee_type, due_date, paid_amount) VALUES (1, 1, 390.0, '2025-07-01T00:00:00', 'Strata fee for Q1 25-26', 'Q1 25-26', True, '2025-05-12T01:26:22.556654', 'billing_period', '2025-07-31T00:00:00', 200.0);
INSERT INTO fee (id, property_id, amount, date, description, period, paid, created_at, fee_type, due_date, paid_amount) VALUES (3, 3, 390.0, '2025-07-01T00:00:00', 'Strata fee for Q1 25-26', 'Q1 25-26', True, '2025-05-12T01:26:22.686349', 'billing_period', '2025-07-31T00:00:00', 390.0);
INSERT INTO fee (id, property_id, amount, date, description, period, paid, created_at, fee_type, due_date, paid_amount) VALUES (5, 2, 300.0, '2025-05-12T07:09:41.026336', 'excess', 'Ad Hoc 2025-05-12', False, '2025-05-12T07:09:41.114440', 'ad_hoc', '2025-05-02T00:00:00', 0.0);
INSERT INTO fee (id, property_id, amount, date, description, period, paid, created_at, fee_type, due_date, paid_amount) VALUES (4, 2, 500.0, '2025-05-12T04:51:34.679527', 'Opening balance', 'Opening Balance', True, '2025-05-12T04:51:34.796135', 'opening_balance', '2025-06-11T04:51:34.679527', 0.0);

-- Table: activity_log
-- 23 rows
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (1, '2025-05-12T08:12:49.862941', 'contact_added', 'Contact Patrick Barber was added to the system', 'Contact', 5);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (2, '2025-05-12T08:38:13.876177', 'expense_added', 'Added new expense: Strata Insurance ($10000.00)', 'Expense', 1);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (3, '2025-05-12T09:25:43.686275', 'payment_reconciled', 'Payment of $200.0 reconciled to property Unit 2 for Opening balance', 'Payment', 4);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (4, '2025-05-12T09:25:43.889028', 'payment_reconciled', 'Payment of $200.0 reconciled to property Unit 2 for Opening balance', 'Payment', 5);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (5, '2025-05-12T09:34:41.071693', 'expense_paid', 'Expense "Strata Insurance" of $10000.0 marked as paid through bank reconciliation (Transaction amount: $10000.0)', 'Expense', 1);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (6, '2025-05-12T09:34:41.267642', 'expense_paid', 'Expense "Strata Insurance" of $10000.0 marked as paid through bank reconciliation (Transaction amount: $10000.0)', 'Expense', 1);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (7, '2025-05-13T00:21:38.718714', 'email_test', 'Test email sent to vaughan@vanheerden.email', NULL, NULL);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (8, '2025-05-14T00:11:15.287655', 'email_test', 'Test email sent to vaughan@vanheerden.email', NULL, NULL);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (9, '2025-05-14T00:11:55.431192', 'email_template_test', 'Test fee_notification template email sent to vaughan@vanheerden.email', NULL, NULL);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (10, '2025-05-14T01:12:37.894461', 'settings_updated', 'Strata settings updated', 'StrataSettings', 1);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (11, '2025-05-14T01:13:22.370641', 'settings_updated', 'Strata settings updated', 'StrataSettings', 1);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (12, '2025-05-14T03:00:42.121443', 'property_added', 'Property 4 was added to the system', 'Property', 4);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (13, '2025-05-14T03:00:55.551236', 'property_deleted', 'Property 4 was deleted from the system', 'Property', 4);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (14, '2025-05-14T03:01:03.748172', 'property_added', 'Property Unit 4 was added to the system', 'Property', 5);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (15, '2025-05-14T03:01:37.833751', 'property_contact_assigned', 'Caren Pullinger was assigned as owner of property Unit 4', 'Property', 5);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (16, '2025-05-14T03:13:59.767050', 'contact_deleted', 'Contact Caren Pullinger was deleted from the system', 'Contact', 4);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (17, '2025-05-14T03:14:19.692013', 'contact_added', 'Contact Cindy was added to the system', 'Contact', 6);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (18, '2025-05-14T03:14:31.324625', 'property_contact_assigned', 'Cindy was assigned as owner of property Unit 4', 'Property', 5);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (19, '2025-05-14T23:54:58.028680', 'contact_updated', 'Contact Florence mellot was updated', 'Contact', 3);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (20, '2025-05-14T23:55:06.562314', 'contact_updated', 'Contact Keith Letcher was updated', 'Contact', 2);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (21, '2025-05-14T23:55:11.966403', 'contact_updated', 'Contact Cindy was updated', 'Contact', 6);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (22, '2025-05-14T23:55:23.101989', 'contact_updated', 'Contact Patrick Barber was updated', 'Contact', 5);
INSERT INTO activity_log (id, timestamp, event_type, description, related_object_type, related_object_id) VALUES (23, '2025-05-14T23:55:28.690677', 'contact_updated', 'Contact Gavin Van Den Heever was updated', 'Contact', 1);

-- Table: expense
-- 1 rows
INSERT INTO expense (id, amount, name, description, due_date, paid, paid_date, invoice_filename, matched_transaction_id, created_at) VALUES (1, 10000.0, 'Strata Insurance', 'building insurance', '2025-05-28T00:00:00', True, '2025-05-12T09:34:41.267237', '20250512083811_Screenshot_2025-05-12_at_09.27.23.png', 'a5f98e2a8901dec592f5563e2056b736', '2025-05-12T08:38:13.667537');

-- Table: user
-- 1 rows
