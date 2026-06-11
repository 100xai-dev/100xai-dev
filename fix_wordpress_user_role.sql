-- WordPress User Role Fix Template
-- Run these queries in your WordPress database (via phpMyAdmin or similar)
-- Replace 'YOUR_USERNAME' with your actual WordPress username

-- First, find the user ID for your username
SELECT ID, user_login, user_email 
FROM wp_users 
WHERE user_login = 'YOUR_USERNAME';

-- Check current user meta (capabilities)
SELECT * 
FROM wp_usermeta 
WHERE user_id = (SELECT ID FROM wp_users WHERE user_login = 'YOUR_USERNAME')
AND (meta_key = 'wp_capabilities' OR meta_key = 'wp_user_level');

-- Fix 1: Give user Administrator role
UPDATE wp_usermeta 
SET meta_value = 'a:1:{s:13:"administrator";b:1;}' 
WHERE user_id = (SELECT ID FROM wp_users WHERE user_login = 'YOUR_USERNAME') 
AND meta_key = 'wp_capabilities';

-- Fix 2: Set user level to 10 (Administrator level)
UPDATE wp_usermeta 
SET meta_value = '10' 
WHERE user_id = (SELECT ID FROM wp_users WHERE user_login = 'YOUR_USERNAME') 
AND meta_key = 'wp_user_level';

-- Alternative: Give Editor role if you prefer (less permissions)
-- UPDATE wp_usermeta 
-- SET meta_value = 'a:1:{s:6:"editor";b:1;}' 
-- WHERE user_id = (SELECT ID FROM wp_users WHERE user_login = 'YOUR_USERNAME') 
-- AND meta_key = 'wp_capabilities';

-- Verify the fix
SELECT u.user_login, um1.meta_value as capabilities, um2.meta_value as user_level
FROM wp_users u
LEFT JOIN wp_usermeta um1 ON u.ID = um1.user_id AND um1.meta_key = 'wp_capabilities'
LEFT JOIN wp_usermeta um2 ON u.ID = um2.user_id AND um2.meta_key = 'wp_user_level'
WHERE u.user_login = 'YOUR_USERNAME';