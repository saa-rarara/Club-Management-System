-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: sau_club_management
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `admin_representatives`
--

DROP TABLE IF EXISTS `admin_representatives`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admin_representatives` (
  `admin_id` int NOT NULL AUTO_INCREMENT,
  `admin_name` varchar(100) NOT NULL,
  `designation` varchar(100) DEFAULT NULL,
  `account_status` varchar(20) NOT NULL,
  PRIMARY KEY (`admin_id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admin_representatives`
--

LOCK TABLES `admin_representatives` WRITE;
/*!40000 ALTER TABLE `admin_representatives` DISABLE KEYS */;
INSERT INTO `admin_representatives` VALUES (1,'Navneet Jha','Dean Of Students','Active'),(2,'Reshma Rastogi (nee Khemchandani)','Faculty In-charge Training & Placements','Active'),(3,'Shubham Mahajan','Assistant Director','Active'),(4,'Swati Chandra','Assistant Warden - Girls Hostel','Active'),(5,'Vineet Ghildyal','Deputy Director (Students Services)','Active'),(6,'Amit Kumar Shukla','Warden Boys Hostel','Active'),(7,'Balram Prasad Raut','Assistant Warden Boys Hostel','Active'),(8,'Deepa Sinha','Proctor','Active'),(9,'Vivek Dixit','Deputy Proctor','Active'),(10,'Priyadarshini K.D.K','Senior Medical Officer','Active');
/*!40000 ALTER TABLE `admin_representatives` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `applications`
--

DROP TABLE IF EXISTS `applications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `applications` (
  `application_id` int NOT NULL AUTO_INCREMENT,
  `club_id` int NOT NULL,
  `student_id` int NOT NULL,
  `title` varchar(150) NOT NULL,
  `description` text,
  `submission_date` datetime NOT NULL,
  `application_status` varchar(30) NOT NULL,
  `proposed_start` datetime NOT NULL,
  `proposed_end` datetime NOT NULL,
  `requested_venue` varchar(150) NOT NULL,
  `event_purpose` text,
  `funding_required` tinyint(1) NOT NULL DEFAULT '0',
  `requested_amount` decimal(12,2) DEFAULT NULL,
  `funding_purpose` text,
  PRIMARY KEY (`application_id`),
  KEY `club_id` (`club_id`),
  KEY `student_id` (`student_id`),
  CONSTRAINT `applications_ibfk_1` FOREIGN KEY (`club_id`) REFERENCES `clubs` (`club_id`),
  CONSTRAINT `applications_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`),
  CONSTRAINT `applications_chk_1` CHECK ((`proposed_end` > `proposed_start`)),
  CONSTRAINT `applications_chk_2` CHECK ((((`funding_required` = false) and (`requested_amount` is null) and (`funding_purpose` is null)) or ((`funding_required` = true) and (`requested_amount` > 0) and (`funding_purpose` is not null))))
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `applications`
--

LOCK TABLES `applications` WRITE;
/*!40000 ALTER TABLE `applications` DISABLE KEYS */;
INSERT INTO `applications` VALUES (1,1,2,'Anime Screening Day','Anime screening and discussion event.','2026-11-18 23:53:03','Approved','2026-12-05 10:00:00','2026-12-05 16:00:00','Auditorium','Promote anime culture.',1,12000.00,'Projector and refreshments.'),(2,2,7,'Annual Theatre Festival','Student theatre and drama competition.','2026-11-18 23:53:03','Approved','2026-12-10 11:00:00','2026-12-10 17:00:00','Main Auditorium','Encourage theatrical talent.',1,25000.00,'Stage setup and costumes.'),(3,3,1,'Battle of Bands','Inter-college music competition.','2026-11-18 23:53:03','Pending','2026-12-15 10:00:00','2026-12-15 18:00:00','Open Air Theatre','Promote musical talent.',1,30000.00,'Sound equipment and prizes.'),(4,5,21,'Creative Writing Competition','Creative writing and poetry competition.','2026-11-18 23:53:03','Approved','2026-12-20 11:00:00','2026-12-20 15:00:00','Seminar Hall','Encourage literary creativity.',0,NULL,NULL),(5,6,12,'Knowledge Quiz','Interdepartmental general knowledge quiz.','2026-11-18 23:53:03','Rejected','2027-01-05 10:00:00','2027-01-05 14:00:00','Conference Hall','Promote knowledge and teamwork.',1,8000.00,'Prizes and event materials.');
/*!40000 ALTER TABLE `applications` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `approval_decisions`
--

DROP TABLE IF EXISTS `approval_decisions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `approval_decisions` (
  `decision_id` int NOT NULL AUTO_INCREMENT,
  `application_id` int NOT NULL,
  `faculty_id` int DEFAULT NULL,
  `admin_id` int DEFAULT NULL,
  `decision` varchar(20) NOT NULL,
  `comments` text,
  `decision_date` datetime NOT NULL,
  PRIMARY KEY (`decision_id`),
  UNIQUE KEY `application_id` (`application_id`,`faculty_id`),
  UNIQUE KEY `application_id_2` (`application_id`,`admin_id`),
  KEY `faculty_id` (`faculty_id`),
  KEY `admin_id` (`admin_id`),
  CONSTRAINT `approval_decisions_ibfk_1` FOREIGN KEY (`application_id`) REFERENCES `applications` (`application_id`),
  CONSTRAINT `approval_decisions_ibfk_2` FOREIGN KEY (`faculty_id`) REFERENCES `faculty_advisors` (`faculty_id`),
  CONSTRAINT `approval_decisions_ibfk_3` FOREIGN KEY (`admin_id`) REFERENCES `admin_representatives` (`admin_id`),
  CONSTRAINT `approval_decisions_chk_1` CHECK ((((`faculty_id` is not null) and (`admin_id` is null)) or ((`faculty_id` is null) and (`admin_id` is not null)))),
  CONSTRAINT `approval_decisions_chk_2` CHECK ((`decision` in (_utf8mb4'Approved',_utf8mb4'Rejected',_utf8mb4'Pending')))
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `approval_decisions`
--

LOCK TABLES `approval_decisions` WRITE;
/*!40000 ALTER TABLE `approval_decisions` DISABLE KEYS */;
INSERT INTO `approval_decisions` VALUES (1,1,NULL,10,'Approved','Application approved.','2026-11-18 00:00:00'),(2,2,16,NULL,'Approved','Application approved.','2026-11-18 00:00:00'),(3,3,NULL,10,'Pending','Awaiting final review.','2026-11-18 00:00:00'),(4,4,16,NULL,'Approved','Application approved.','2026-11-18 00:00:00'),(5,5,NULL,10,'Rejected','Application rejected.','2026-11-18 00:00:00');
/*!40000 ALTER TABLE `approval_decisions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `club_advisor`
--

DROP TABLE IF EXISTS `club_advisor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `club_advisor` (
  `advisor_assignment_id` int NOT NULL AUTO_INCREMENT,
  `faculty_id` int NOT NULL,
  `club_id` int NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `assignment_status` varchar(20) NOT NULL,
  PRIMARY KEY (`advisor_assignment_id`),
  KEY `faculty_id` (`faculty_id`),
  KEY `club_id` (`club_id`),
  CONSTRAINT `club_advisor_ibfk_1` FOREIGN KEY (`faculty_id`) REFERENCES `faculty_advisors` (`faculty_id`),
  CONSTRAINT `club_advisor_ibfk_2` FOREIGN KEY (`club_id`) REFERENCES `clubs` (`club_id`),
  CONSTRAINT `club_advisor_chk_1` CHECK (((`end_date` is null) or (`end_date` >= `start_date`)))
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `club_advisor`
--

LOCK TABLES `club_advisor` WRITE;
/*!40000 ALTER TABLE `club_advisor` DISABLE KEYS */;
INSERT INTO `club_advisor` VALUES (1,12,1,'2026-11-18',NULL,'Active'),(2,3,2,'2026-11-18',NULL,'Active'),(3,8,3,'2026-11-18',NULL,'Active'),(4,16,4,'2026-11-18',NULL,'Active'),(5,5,5,'2026-11-18',NULL,'Active'),(6,16,6,'2026-11-18',NULL,'Active'),(7,16,7,'2026-11-18',NULL,'Active'),(8,14,8,'2026-11-18',NULL,'Active'),(9,2,9,'2026-11-18',NULL,'Active'),(10,18,10,'2026-11-18',NULL,'Active');
/*!40000 ALTER TABLE `club_advisor` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `club_president`
--

DROP TABLE IF EXISTS `club_president`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `club_president` (
  `president_assignment_id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `club_id` int NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `assignment_status` varchar(20) NOT NULL,
  PRIMARY KEY (`president_assignment_id`),
  KEY `student_id` (`student_id`,`club_id`),
  CONSTRAINT `club_president_ibfk_1` FOREIGN KEY (`student_id`, `club_id`) REFERENCES `memberships` (`student_id`, `club_id`),
  CONSTRAINT `club_president_chk_1` CHECK (((`end_date` is null) or (`end_date` >= `start_date`)))
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `club_president`
--

LOCK TABLES `club_president` WRITE;
/*!40000 ALTER TABLE `club_president` DISABLE KEYS */;
INSERT INTO `club_president` VALUES (1,19,1,'2026-11-18',NULL,'Active'),(2,79,2,'2026-11-18',NULL,'Active'),(3,65,3,'2026-11-18',NULL,'Active'),(4,93,4,'2026-11-18',NULL,'Active'),(5,76,5,'2026-11-18',NULL,'Active'),(6,94,6,'2026-11-18',NULL,'Active'),(7,3,7,'2026-11-18',NULL,'Active'),(8,104,8,'2026-11-18',NULL,'Active'),(9,98,9,'2026-11-18',NULL,'Active'),(10,106,10,'2026-11-18',NULL,'Active');
/*!40000 ALTER TABLE `club_president` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `clubs`
--

DROP TABLE IF EXISTS `clubs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `clubs` (
  `club_id` int NOT NULL AUTO_INCREMENT,
  `club_name` varchar(100) NOT NULL,
  `club_status` varchar(20) NOT NULL,
  PRIMARY KEY (`club_id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `clubs`
--

LOCK TABLES `clubs` WRITE;
/*!40000 ALTER TABLE `clubs` DISABLE KEYS */;
INSERT INTO `clubs` VALUES (1,'Anime club','Active'),(2,'Tamasha','Active'),(3,'Music Club','Active'),(4,'Tinker Town','Active'),(5,'Kalamkar','Active'),(6,'Takshila','Active'),(7,'Photography Club','Active'),(8,'Dance Club','Active'),(9,'CSTC','Active'),(10,'CSI','Active');
/*!40000 ALTER TABLE `clubs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `faculty_advisors`
--

DROP TABLE IF EXISTS `faculty_advisors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `faculty_advisors` (
  `faculty_id` int NOT NULL AUTO_INCREMENT,
  `faculty_name` varchar(100) NOT NULL,
  `department` varchar(100) DEFAULT NULL,
  `account_status` varchar(20) NOT NULL,
  PRIMARY KEY (`faculty_id`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `faculty_advisors`
--

LOCK TABLES `faculty_advisors` WRITE;
/*!40000 ALTER TABLE `faculty_advisors` DISABLE KEYS */;
INSERT INTO `faculty_advisors` VALUES (1,'Pranab Kumar Muhuri','Faculty of Engineering and Technology','Active'),(2,'Muhammad Abulaish','Faculty of Engineering and Technology','Active'),(3,'Kavita Khanna','Faculty of Engineering and Technology','Active'),(4,'Nasib Singh Gill','Faculty of Engineering and Technology','Active'),(5,'Amita Dev','Faculty of Engineering and Technology','Active'),(6,'Reshma Rastogi','Faculty of Engineering and Technology','Active'),(7,'Amit Banerjee','Faculty of Engineering and Technology','Active'),(8,'Bijoy Chand Chatterjee','Faculty of Engineering and Technology','Active'),(9,'Shachi Sharma','Faculty of Engineering and Technology','Active'),(10,'Tamalika Chaira','Faculty of Engineering and Technology','Active'),(11,'Amit K. Shukla','Faculty of Engineering and Technology','Active'),(12,'Ashwini B','Faculty of Engineering and Technology','Active'),(13,'Shashank Sheshar Singh','Faculty of Engineering and Technology','Active'),(14,'Rajesh Ranjan','Faculty of Engineering and Technology','Active'),(15,'Anurag Tiwari','Faculty of Engineering and Technology','Active'),(16,'Sandeep Kumar','Faculty of Engineering and Technology','Active'),(17,'Ankit Jain','Faculty of Engineering and Technology','Active'),(18,'Neha Agrawal','Faculty of Engineering and Technology','Active'),(19,'Alok Agarwal','Faculty of Engineering and Technology','Active'),(20,'Chandra Bhushan Kumar','Faculty of Engineering and Technology','Active'),(21,'Taniya Seth','Faculty of Engineering and Technology','Active'),(22,'Praveen','Faculty of Engineering and Technology','Active');
/*!40000 ALTER TABLE `faculty_advisors` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `memberships`
--

DROP TABLE IF EXISTS `memberships`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `memberships` (
  `student_id` int NOT NULL,
  `club_id` int NOT NULL,
  `join_date` date NOT NULL,
  `membership_status` varchar(20) NOT NULL,
  PRIMARY KEY (`student_id`,`club_id`),
  KEY `club_id` (`club_id`),
  CONSTRAINT `memberships_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`),
  CONSTRAINT `memberships_ibfk_2` FOREIGN KEY (`club_id`) REFERENCES `clubs` (`club_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `memberships`
--

LOCK TABLES `memberships` WRITE;
/*!40000 ALTER TABLE `memberships` DISABLE KEYS */;
INSERT INTO `memberships` VALUES (1,3,'2026-11-18','Active'),(2,1,'2026-11-18','Active'),(3,7,'2026-11-18','Active'),(4,1,'2026-11-18','Active'),(5,3,'2026-11-18','Active'),(6,3,'2026-11-18','Active'),(7,2,'2026-11-18','Active'),(8,10,'2026-11-18','Active'),(9,3,'2026-11-18','Active'),(10,4,'2026-11-18','Active'),(11,10,'2026-11-18','Active'),(12,6,'2026-11-18','Active'),(13,6,'2026-11-18','Active'),(14,4,'2026-11-18','Active'),(15,8,'2026-11-18','Active'),(16,2,'2026-11-18','Active'),(17,3,'2026-11-18','Active'),(18,3,'2026-11-18','Active'),(19,1,'2026-11-18','Active'),(20,7,'2026-11-18','Active'),(21,5,'2026-11-18','Active'),(22,7,'2026-11-18','Active'),(23,8,'2026-11-18','Active'),(24,5,'2026-11-18','Active'),(25,1,'2026-11-18','Active'),(26,3,'2026-11-18','Active'),(27,6,'2026-11-18','Active'),(28,9,'2026-11-18','Active'),(29,3,'2026-11-18','Active'),(30,6,'2026-11-18','Active'),(31,8,'2026-11-18','Active'),(32,1,'2026-11-18','Active'),(33,5,'2026-11-18','Active'),(34,7,'2026-11-18','Active'),(35,2,'2026-11-18','Active'),(36,6,'2026-11-18','Active'),(37,2,'2026-11-18','Active'),(38,10,'2026-11-18','Active'),(39,6,'2026-11-18','Active'),(40,4,'2026-11-18','Active'),(41,2,'2026-11-18','Active'),(42,8,'2026-11-18','Active'),(43,3,'2026-11-18','Active'),(44,2,'2026-11-18','Active'),(45,3,'2026-11-18','Active'),(46,4,'2026-11-18','Active'),(47,4,'2026-11-18','Active'),(48,1,'2026-11-18','Active'),(49,6,'2026-11-18','Active'),(50,8,'2026-11-18','Active'),(51,7,'2026-11-18','Active'),(52,5,'2026-11-18','Active'),(53,5,'2026-11-18','Active'),(54,6,'2026-11-18','Active'),(55,7,'2026-11-18','Active'),(56,8,'2026-11-18','Active'),(57,7,'2026-11-18','Active'),(58,1,'2026-11-18','Active'),(59,8,'2026-11-18','Active'),(60,4,'2026-11-18','Active'),(61,4,'2026-11-18','Active'),(62,8,'2026-11-18','Active'),(63,9,'2026-11-18','Active'),(64,2,'2026-11-18','Active'),(65,3,'2026-11-18','Active'),(66,3,'2026-11-18','Active'),(67,6,'2026-11-18','Active'),(68,1,'2026-11-18','Active'),(69,9,'2026-11-18','Active'),(70,4,'2026-11-18','Active'),(71,7,'2026-11-18','Active'),(72,7,'2026-11-18','Active'),(73,5,'2026-11-18','Active'),(74,5,'2026-11-18','Active'),(75,10,'2026-11-18','Active'),(76,5,'2026-11-18','Active'),(77,7,'2026-11-18','Active'),(78,9,'2026-11-18','Active'),(79,2,'2026-11-18','Active'),(80,8,'2026-11-18','Active'),(81,3,'2026-11-18','Active'),(82,4,'2026-11-18','Active'),(83,5,'2026-11-18','Active'),(84,1,'2026-11-18','Active'),(85,8,'2026-11-18','Active'),(86,8,'2026-11-18','Active'),(87,7,'2026-11-18','Active'),(88,6,'2026-11-18','Active'),(89,7,'2026-11-18','Active'),(90,5,'2026-11-18','Active'),(91,3,'2026-11-18','Active'),(92,7,'2026-11-18','Active'),(93,4,'2026-11-18','Active'),(94,6,'2026-11-18','Active'),(95,4,'2026-11-18','Active'),(96,10,'2026-11-18','Active'),(97,1,'2026-11-18','Active'),(98,9,'2026-11-18','Active'),(99,4,'2026-11-18','Active'),(100,3,'2026-11-18','Active'),(101,2,'2026-11-18','Active'),(102,5,'2026-11-18','Active'),(103,3,'2026-11-18','Active'),(104,8,'2026-11-18','Active'),(105,4,'2026-11-18','Active'),(106,10,'2026-11-18','Active');
/*!40000 ALTER TABLE `memberships` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `students`
--

DROP TABLE IF EXISTS `students`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `students` (
  `student_id` int NOT NULL AUTO_INCREMENT,
  `student_name` varchar(100) NOT NULL,
  `department` varchar(100) DEFAULT NULL,
  `program` varchar(100) DEFAULT NULL,
  `account_status` varchar(20) NOT NULL,
  PRIMARY KEY (`student_id`)
) ENGINE=InnoDB AUTO_INCREMENT=107 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `students`
--

LOCK TABLES `students` WRITE;
/*!40000 ALTER TABLE `students` DISABLE KEYS */;
INSERT INTO `students` VALUES (1,'Aanvi Sharma','Computer Science & Engineering','BTech / Dual Degree','Active'),(2,'Achyut Krishna Sharma','Computer Science & Engineering','BTech / Dual Degree','Active'),(3,'Adarsh Raj','Computer Science & Engineering','BTech / Dual Degree','Active'),(4,'Aditi Rajput','Computer Science & Engineering','BTech / Dual Degree','Active'),(5,'Aditya Adhikari','Computer Science & Engineering','BTech / Dual Degree','Active'),(6,'Aditya Kumar','Computer Science & Engineering','BTech / Dual Degree','Active'),(7,'Aditya Raj Singh','Computer Science & Engineering','BTech / Dual Degree','Active'),(8,'Adivi Ananya','Computer Science & Engineering','BTech / Dual Degree','Active'),(9,'Amar Kumar','Computer Science & Engineering','BTech / Dual Degree','Active'),(10,'Ameetesh Awadh','Computer Science & Engineering','BTech / Dual Degree','Active'),(11,'Ansh Kumar','Computer Science & Engineering','BTech / Dual Degree','Active'),(12,'Anshika Gupta','Computer Science & Engineering','BTech / Dual Degree','Active'),(13,'Anuj Kumar','Computer Science & Engineering','BTech / Dual Degree','Active'),(14,'Anuja Kumari','Computer Science & Engineering','BTech / Dual Degree','Active'),(15,'Anushka Verma','Computer Science & Engineering','BTech / Dual Degree','Active'),(16,'Anushy','Computer Science & Engineering','BTech / Dual Degree','Active'),(17,'Arnav Mishra','Computer Science & Engineering','BTech / Dual Degree','Active'),(18,'Arnav Sood','Computer Science & Engineering','BTech / Dual Degree','Active'),(19,'Arnav Srivastava','Computer Science & Engineering','BTech / Dual Degree','Active'),(20,'Aswin Karthick M','Computer Science & Engineering','BTech / Dual Degree','Active'),(21,'Atul Kashyap','Computer Science & Engineering','BTech / Dual Degree','Active'),(22,'Avinash Kumar','Computer Science & Engineering','BTech / Dual Degree','Active'),(23,'Bhavana Gupta','Computer Science & Engineering','BTech / Dual Degree','Active'),(24,'Bodapatla Divyendu','Computer Science & Engineering','BTech / Dual Degree','Active'),(25,'Chintan Kumar Singal','Computer Science & Engineering','BTech / Dual Degree','Active'),(26,'Chitra Sharma','Computer Science & Engineering','BTech / Dual Degree','Active'),(27,'Deepshikha Kushwaha','Computer Science & Engineering','BTech / Dual Degree','Active'),(28,'Deep Yadav','Computer Science & Engineering','BTech / Dual Degree','Active'),(29,'Dhairya Solanki','Computer Science & Engineering','BTech / Dual Degree','Active'),(30,'Farhan Akhlaq','Computer Science & Engineering','BTech / Dual Degree','Active'),(31,'Harkeerat Singh','Computer Science & Engineering','BTech / Dual Degree','Active'),(32,'Harsh Mittal','Computer Science & Engineering','BTech / Dual Degree','Active'),(33,'Ipsita Bajpai','Computer Science & Engineering','BTech / Dual Degree','Active'),(34,'Karthik Baurai','Computer Science & Engineering','BTech / Dual Degree','Active'),(35,'Keshav Mittal','Computer Science & Engineering','BTech / Dual Degree','Active'),(36,'Kishlay','Computer Science & Engineering','BTech / Dual Degree','Active'),(37,'Lavanya Sharma','Computer Science & Engineering','BTech / Dual Degree','Active'),(38,'Madhav Rana','Computer Science & Engineering','BTech / Dual Degree','Active'),(39,'Mahi','Computer Science & Engineering','BTech / Dual Degree','Active'),(40,'Misbah Ul Islam','Computer Science & Engineering','BTech / Dual Degree','Active'),(41,'Mukund Prasad','Computer Science & Engineering','BTech / Dual Degree','Active'),(42,'Nandan Bajgain','Computer Science & Engineering','BTech / Dual Degree','Active'),(43,'Nikhil Anand','Computer Science & Engineering','BTech / Dual Degree','Active'),(44,'Nikhil Rai','Computer Science & Engineering','BTech / Dual Degree','Active'),(45,'Nikhil Rana','Computer Science & Engineering','BTech / Dual Degree','Active'),(46,'Nisha Singh','Computer Science & Engineering','BTech / Dual Degree','Active'),(47,'Nishant Sharma','Computer Science & Engineering','BTech / Dual Degree','Active'),(48,'Nitesh Sharma','Computer Science & Engineering','BTech / Dual Degree','Active'),(49,'Pagilla Prateek Reddy','Computer Science & Engineering','BTech / Dual Degree','Active'),(50,'Prakash Sharma','Computer Science & Engineering','BTech / Dual Degree','Active'),(51,'Prakhar Parashar','Computer Science & Engineering','BTech / Dual Degree','Active'),(52,'Atirek Sharma','Computer Science & Engineering','BTech / Dual Degree','Active'),(53,'Nikhil Malik','Computer Science & Engineering','BTech / Dual Degree','Active'),(54,'Aashta Bahuguna','Computer Science & Engineering','BTech / Dual Degree','Active'),(55,'Raj Nath Pandey','Computer Science & Engineering','BTech / Dual Degree','Active'),(56,'Rupika Chalamalla','Computer Science & Engineering','BTech / Dual Degree','Active'),(57,'Rushil','Computer Science & Engineering','BTech / Dual Degree','Active'),(58,'Saara Ahmed','Computer Science & Engineering','BTech / Dual Degree','Active'),(59,'Sania Shanty','Computer Science & Engineering','BTech / Dual Degree','Active'),(60,'Sanskriti Singh','Computer Science & Engineering','BTech / Dual Degree','Active'),(61,'Saumya Parashar','Computer Science & Engineering','BTech / Dual Degree','Active'),(62,'Saurabh Singh','Computer Science & Engineering','BTech / Dual Degree','Active'),(63,'Shri Mahaveer','Computer Science & Engineering','BTech / Dual Degree','Active'),(64,'Shruti Sharma','Computer Science & Engineering','BTech / Dual Degree','Active'),(65,'Shubham Kumar Yadav','Computer Science & Engineering','BTech / Dual Degree','Active'),(66,'Siddhant Choudhary','Computer Science & Engineering','BTech / Dual Degree','Active'),(67,'Kalamacheru Siddhartha','Computer Science & Engineering','BTech / Dual Degree','Active'),(68,'Sparsh Samrat','Computer Science & Engineering','BTech / Dual Degree','Active'),(69,'Subham Agarwal','Computer Science & Engineering','BTech / Dual Degree','Active'),(70,'Suruchi Singh','Computer Science & Engineering','BTech / Dual Degree','Active'),(71,'Surya Pratap Singh','Computer Science & Engineering','BTech / Dual Degree','Active'),(72,'Suryanshu Singh','Computer Science & Engineering','BTech / Dual Degree','Active'),(73,'Suyash Singh Gusain','Computer Science & Engineering','BTech / Dual Degree','Active'),(74,'Tanmay Madan','Computer Science & Engineering','BTech / Dual Degree','Active'),(75,'Tarini Parashar','Computer Science & Engineering','BTech / Dual Degree','Active'),(76,'Tarun Das','Computer Science & Engineering','BTech / Dual Degree','Active'),(77,'Titas Mahato','Computer Science & Engineering','BTech / Dual Degree','Active'),(78,'Upasana Sarmah','Computer Science & Engineering','BTech / Dual Degree','Active'),(79,'Utkarsh','Computer Science & Engineering','BTech / Dual Degree','Active'),(80,'Vedansh Kaushik','Computer Science & Engineering','BTech / Dual Degree','Active'),(81,'Vikryansh Singh','Computer Science & Engineering','BTech / Dual Degree','Active'),(82,'Vipin Chaudhary','Computer Science & Engineering','BTech / Dual Degree','Active'),(83,'Yash Tomar','Computer Science & Engineering','BTech / Dual Degree','Active'),(84,'Sabhyata Bharti','Computer Science & Engineering','BTech / Dual Degree','Active'),(85,'Rohit Kumar','Computer Science & Engineering','BTech / Dual Degree','Active'),(86,'Syed Hasan Abbas','Computer Science & Engineering','BTech / Dual Degree','Active'),(87,'Siya Singhal','Computer Science & Engineering','BTech / Dual Degree','Active'),(88,'Yajat Krishnan','Computer Science & Engineering','BTech / Dual Degree','Active'),(89,'Uddhrithi Chowdhury','Computer Science & Engineering','BTech / Dual Degree','Active'),(90,'Hansika Malik','Computer Science & Engineering','BTech / Dual Degree','Active'),(91,'Krish Singh','Computer Science & Engineering','BTech / Dual Degree','Active'),(92,'Saksham Prabhakar','Computer Science & Engineering','BTech / Dual Degree','Active'),(93,'Siddharth Prabhakar','Computer Science & Engineering','BTech / Dual Degree','Active'),(94,'Rabiya Khan','Computer Science & Engineering','BTech / Dual Degree','Active'),(95,'K. Ribhu','Computer Science & Engineering','BTech / Dual Degree','Active'),(96,'Madhav Kathuria','Computer Science & Engineering','BTech / Dual Degree','Active'),(97,'Harsh Raj','Computer Science & Engineering','BTech / Dual Degree','Active'),(98,'Arkodyuti Bhattacharyya','Computer Science & Engineering','BTech / Dual Degree','Active'),(99,'Utkarsh Jha','Computer Science & Engineering','BTech / Dual Degree','Active'),(100,'Vaibhav Tripathi','Computer Science & Engineering','BTech / Dual Degree','Active'),(101,'Vijay Ramesh','Computer Science & Engineering','BTech / Dual Degree','Active'),(102,'Asif Ahmad','Computer Science & Engineering','BTech / Dual Degree','Active'),(103,'Aaryaveer Rathore','Computer Science & Engineering','BTech / Dual Degree','Active'),(104,'Amritha S Nair','Computer Science & Engineering','BTech / Dual Degree','Active'),(105,'Intekhab Akhtar','Computer Science & Engineering','BTech / Dual Degree','Active'),(106,'Swarnojwal Guha','Computer Science & Engineering','BTech / Dual Degree','Active');
/*!40000 ALTER TABLE `students` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_accounts`
--

DROP TABLE IF EXISTS `user_accounts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_accounts` (
  `account_id` int NOT NULL AUTO_INCREMENT,
  `student_id` int DEFAULT NULL,
  `faculty_id` int DEFAULT NULL,
  `admin_id` int DEFAULT NULL,
  `username` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  PRIMARY KEY (`account_id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `student_id` (`student_id`),
  UNIQUE KEY `faculty_id` (`faculty_id`),
  UNIQUE KEY `admin_id` (`admin_id`),
  CONSTRAINT `user_accounts_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`),
  CONSTRAINT `user_accounts_ibfk_2` FOREIGN KEY (`faculty_id`) REFERENCES `faculty_advisors` (`faculty_id`),
  CONSTRAINT `user_accounts_ibfk_3` FOREIGN KEY (`admin_id`) REFERENCES `admin_representatives` (`admin_id`),
  CONSTRAINT `user_accounts_chk_1` CHECK (((((`student_id` is not null) + (`faculty_id` is not null)) + (`admin_id` is not null)) = 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_accounts`
--

LOCK TABLES `user_accounts` WRITE;
/*!40000 ALTER TABLE `user_accounts` DISABLE KEYS */;
/*!40000 ALTER TABLE `user_accounts` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-19 12:44:06
