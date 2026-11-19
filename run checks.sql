USE SAU_Club_Management;

SELECT s.*
FROM Students s
JOIN Memberships m ON s.student_id = m.student_id
JOIN Clubs c ON m.club_id = c.club_id
WHERE c.club_name = 'Anime Club';

SELECT f.faculty_name, c.club_name
FROM Faculty_Advisors f
JOIN Club_Advisor ca ON f.faculty_id = ca.faculty_id
JOIN Clubs c ON ca.club_id = c.club_id
WHERE c.club_name = 'Tinker Town';


SELECT s.student_name, c.club_name
FROM Club_President cp
JOIN Students s ON cp.student_id = s.student_id
JOIN Clubs c ON cp.club_id = c.club_id
WHERE c.club_name = 'Tamasha';

SELECT s.student_name, c.club_name, a.title, a.application_status
FROM Applications a
JOIN Students s ON a.student_id = s.student_id
JOIN Clubs c ON a.club_id = c.club_id;

SELECT s.student_name, c.club_name, cp.assignment_status
FROM Club_President cp
JOIN Students s ON cp.student_id = s.student_id
JOIN Clubs c ON cp.club_id = c.club_id;