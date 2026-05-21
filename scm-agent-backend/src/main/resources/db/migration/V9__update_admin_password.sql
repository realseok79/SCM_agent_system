-- db/migration/V9__update_admin_password.sql
UPDATE users
SET password = '$2a$10$i0EeL3itn6cq8DZ7khpY/uCa.4nXqq6wnTRnHYpIpm4xxG3FwSWWa'
WHERE username = 'admin';
