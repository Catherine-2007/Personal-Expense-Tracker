-- SpendSense-XAI  |  MySQL / MariaDB import file (works in XAMPP phpMyAdmin)
-- HOW TO IMPORT: phpMyAdmin -> create/select an empty database -> Import tab ->
-- choose THIS .sql file -> Go.   (Do NOT import backend/spendsense.db: that is a
-- binary SQLite file and phpMyAdmin cannot read it.)
-- Contains all tables plus demo accounts: demo@spendsense.app / demo1234

/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
DROP TABLE IF EXISTS `budgets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `category` varchar(60) NOT NULL,
  `monthly_limit` float NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_budgets_id` (`id`),
  KEY `ix_budgets_user_id` (`user_id`),
  CONSTRAINT `budgets_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

DROP TABLE IF EXISTS `expenses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `expenses` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `amount` float NOT NULL,
  `category` varchar(100) NOT NULL,
  `merchant` varchar(200) DEFAULT NULL,
  `payment_method` varchar(30) DEFAULT NULL,
  `note` varchar(500) DEFAULT NULL,
  `source` varchar(20) DEFAULT NULL,
  `timestamp` datetime DEFAULT NULL,
  `location` varchar(200) DEFAULT NULL,
  `device_usage` varchar(20) DEFAULT NULL,
  `screen_time_minutes` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `ix_expenses_timestamp` (`timestamp`),
  KEY `ix_expenses_id` (`id`),
  CONSTRAINT `expenses_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=118 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

INSERT INTO `expenses` (`id`, `user_id`, `amount`, `category`, `merchant`, `payment_method`, `note`, `source`, `timestamp`, `location`, `device_usage`, `screen_time_minutes`, `created_at`) VALUES (1,1,360.01,'Food','Dominos','UPI','late night order','manual','2026-10-24 22:08:36','Home','',44,'2026-10-24 16:24:36'),
(2,1,418.77,'Food','Dominos','UPI','late night order','manual','2026-10-24 22:05:36','Home','',31,'2026-10-24 16:24:36'),
(3,1,329.54,'Food','Dominos','UPI','late night order','manual','2026-10-16 22:44:36','Home','',71,'2026-10-24 16:24:36'),
(4,1,485.71,'Food','Zomato','UPI','late night order','manual','2026-10-07 23:55:36','Home','',81,'2026-10-24 16:24:36'),
(5,1,419.05,'Food','Dominos','UPI','late night order','manual','2026-10-10 23:09:36','Home','',47,'2026-10-24 16:24:36'),
(6,1,401.97,'Food','Swiggy','UPI','late night order','manual','2026-10-01 22:54:36','Home','',52,'2026-10-24 16:24:36'),
(7,1,541.89,'Food','Swiggy','UPI','late night order','manual','2026-09-22 00:07:36','Home','',64,'2026-10-24 16:24:36'),
(8,1,497.41,'Food','Dominos','UPI','late night order','manual','2026-09-19 00:23:36','Home','',85,'2026-10-24 16:24:36'),
(9,1,514.51,'Food','Swiggy','UPI','late night order','manual','2026-09-11 22:18:36','Home','',79,'2026-10-24 16:24:36'),
(10,1,402.05,'Food','Swiggy','UPI','late night order','manual','2026-09-12 23:40:36','Home','',59,'2026-10-24 16:24:36'),
(11,1,333.8,'Food','Zomato','UPI','late night order','manual','2026-09-04 00:44:36','Home','',47,'2026-10-24 16:24:36'),
(12,1,541.65,'Food','Dominos','UPI','late night order','manual','2026-08-29 23:29:36','Home','',40,'2026-10-24 16:24:36'),
(13,1,525.26,'Food','Dominos','UPI','late night order','manual','2026-08-26 00:43:36','Home','',44,'2026-10-24 16:24:36'),
(14,1,572.02,'Food','Swiggy','UPI','late night order','manual','2026-08-22 23:17:36','Home','',55,'2026-10-24 16:24:36'),
(15,1,512.18,'Food','Swiggy','UPI','late night order','manual','2026-08-14 00:56:36','Home','',55,'2026-10-24 16:24:36'),
(16,1,305.85,'Food','Zomato','UPI','late night order','manual','2026-08-05 23:35:36','Home','',77,'2026-10-24 16:24:36'),
(17,1,483.83,'Food','Dominos','UPI','late night order','manual','2026-08-04 00:37:36','Home','',87,'2026-10-24 16:24:36'),
(18,1,1039.64,'Groceries','BigBasket','Card','','manual','2026-10-22 11:14:36','Home','',0,'2026-10-24 16:24:36'),
(19,1,1398.4,'Groceries','BigBasket','Card','','manual','2026-10-15 11:08:36','Home','',0,'2026-10-24 16:24:36'),
(20,1,1105.72,'Groceries','BigBasket','Card','','manual','2026-10-08 11:05:36','Home','',0,'2026-10-24 16:24:36'),
(21,1,1253.47,'Groceries','BigBasket','Card','','manual','2026-10-01 11:55:36','Home','',0,'2026-10-24 16:24:36'),
(22,1,865.79,'Groceries','BigBasket','Card','','manual','2026-09-24 11:40:36','Home','',0,'2026-10-24 16:24:36'),
(23,1,895.99,'Groceries','BigBasket','Card','','manual','2026-09-17 11:43:36','Home','',0,'2026-10-24 16:24:36'),
(24,1,1053.3,'Groceries','BigBasket','Card','','manual','2026-09-10 11:04:36','Home','',0,'2026-10-24 16:24:36'),
(25,1,1030.86,'Groceries','BigBasket','Card','','manual','2026-09-03 11:38:36','Home','',0,'2026-10-24 16:24:36'),
(26,1,1397.67,'Groceries','BigBasket','Card','','manual','2026-08-27 11:33:36','Home','',0,'2026-10-24 16:24:36'),
(27,1,950.85,'Groceries','BigBasket','Card','','manual','2026-08-20 11:35:36','Home','',0,'2026-10-24 16:24:36'),
(28,1,1316.47,'Groceries','BigBasket','Card','','manual','2026-08-13 11:00:36','Home','',0,'2026-10-24 16:24:36'),
(29,1,1208.17,'Groceries','BigBasket','Card','','manual','2026-08-06 11:07:36','Home','',0,'2026-10-24 16:24:36'),
(30,1,104.54,'Transport','Uber','UPI','','manual','2026-10-22 18:27:36','Home','',0,'2026-10-24 16:24:36'),
(31,1,289.84,'Transport','Uber','UPI','','manual','2026-10-21 08:56:36','Home','',0,'2026-10-24 16:24:36'),
(32,1,265.17,'Transport','Uber','UPI','','manual','2026-10-16 18:32:36','Home','',0,'2026-10-24 16:24:36'),
(33,1,198.66,'Transport','Uber','UPI','','manual','2026-10-14 09:49:36','Home','',0,'2026-10-24 16:24:36'),
(34,1,273.32,'Transport','Uber','UPI','','manual','2026-10-09 18:53:36','Home','',0,'2026-10-24 16:24:36'),
(35,1,273.16,'Transport','Uber','UPI','','manual','2026-10-07 09:05:36','Home','',0,'2026-10-24 16:24:36'),
(36,1,259.53,'Transport','Uber','UPI','','manual','2026-10-06 19:48:36','Home','',0,'2026-10-24 16:24:36'),
(37,1,288.31,'Transport','Uber','UPI','','manual','2026-10-04 19:10:36','Home','',0,'2026-10-24 16:24:36'),
(38,1,292.16,'Transport','Uber','UPI','','manual','2026-10-03 19:59:36','Home','',0,'2026-10-24 16:24:36'),
(39,1,167.78,'Transport','Uber','UPI','','manual','2026-09-30 18:42:36','Home','',0,'2026-10-24 16:24:36'),
(40,1,94.09,'Transport','Uber','UPI','','manual','2026-09-26 09:01:36','Home','',0,'2026-10-24 16:24:36'),
(41,1,81.58,'Transport','Uber','UPI','','manual','2026-09-24 09:45:36','Home','',0,'2026-10-24 16:24:36'),
(42,1,269.12,'Transport','Uber','UPI','','manual','2026-09-22 08:04:36','Home','',0,'2026-10-24 16:24:36'),
(43,1,127.13,'Transport','Uber','UPI','','manual','2026-09-20 19:08:36','Home','',0,'2026-10-24 16:24:36'),
(44,1,257.65,'Transport','Uber','UPI','','manual','2026-09-16 19:12:36','Home','',0,'2026-10-24 16:24:36'),
(45,1,157.95,'Transport','Uber','UPI','','manual','2026-09-15 19:26:36','Home','',0,'2026-10-24 16:24:36'),
(46,1,240.21,'Transport','Uber','UPI','','manual','2026-09-10 19:51:36','Home','',0,'2026-10-24 16:24:36'),
(47,1,197.98,'Transport','Uber','UPI','','manual','2026-09-08 09:08:36','Home','',0,'2026-10-24 16:24:36'),
(48,1,272.39,'Transport','Uber','UPI','','manual','2026-09-06 09:04:36','Home','',0,'2026-10-24 16:24:36'),
(49,1,293.18,'Transport','Uber','UPI','','manual','2026-09-02 08:59:36','Home','',0,'2026-10-24 16:24:36'),
(50,1,186.84,'Transport','Uber','UPI','','manual','2026-08-31 19:13:36','Home','',0,'2026-10-24 16:24:36'),
(51,1,296.77,'Transport','Uber','UPI','','manual','2026-08-28 08:16:36','Home','',0,'2026-10-24 16:24:36'),
(52,1,917.95,'Shopping','Myntra','Card','','manual','2026-09-18 20:18:36','Home','',0,'2026-10-24 16:24:36'),
(53,1,2519.53,'Shopping','Amazon','Card','','manual','2026-09-27 13:03:36','Home','',0,'2026-10-24 16:24:36'),
(54,1,1857.7,'Shopping','Myntra','Card','','manual','2026-10-18 22:54:36','Home','',0,'2026-10-24 16:24:36'),
(55,1,3094.1,'Shopping','Amazon','Card','','manual','2026-08-18 13:05:36','Home','',0,'2026-10-24 16:24:36'),
(56,1,2323.07,'Shopping','Amazon','Card','','manual','2026-10-01 13:15:36','Home','',0,'2026-10-24 16:24:36'),
(57,1,2063.08,'Shopping','Amazon','Card','','manual','2026-09-03 13:02:36','Home','',0,'2026-10-24 16:24:36'),
(58,1,2274.91,'Shopping','Myntra','Card','','manual','2026-08-06 13:36:36','Home','',0,'2026-10-24 16:24:36'),
(59,1,1051.5,'Shopping','Myntra','Card','','manual','2026-08-19 20:45:36','Home','',0,'2026-10-24 16:24:36'),
(60,1,1388.51,'Bills','Electricity Board','Bank','','manual','2026-10-23 10:16:36','Home','',0,'2026-10-24 16:24:36'),
(61,1,1437.47,'Bills','Electricity Board','Bank','','manual','2026-09-23 10:42:36','Home','',0,'2026-10-24 16:24:36'),
(62,1,1587.3,'Bills','Electricity Board','Bank','','manual','2026-08-24 10:29:36','Home','',0,'2026-10-24 16:24:36'),
(63,1,649,'Bills','Netflix','Card','subscription','manual','2026-10-21 09:30:00','','',0,'2026-10-24 16:24:36'),
(64,1,139,'Bills','Spotify','UPI','subscription','manual','2026-10-15 09:30:00','','',0,'2026-10-24 16:24:36'),
(65,1,1500,'Health','Cult Gym','UPI','subscription','manual','2026-10-10 09:30:00','','',0,'2026-10-24 16:24:36'),
(66,1,649,'Bills','Netflix','Card','subscription','manual','2026-09-21 09:30:00','','',0,'2026-10-24 16:24:36'),
(67,1,119,'Bills','Spotify','UPI','subscription','manual','2026-09-15 09:30:00','','',0,'2026-10-24 16:24:36'),
(68,1,1500,'Health','Cult Gym','UPI','subscription','manual','2026-09-10 09:30:00','','',0,'2026-10-24 16:24:36'),
(69,1,649,'Bills','Netflix','Card','subscription','manual','2026-08-22 09:30:00','','',0,'2026-10-24 16:24:36'),
(70,1,119,'Bills','Spotify','UPI','subscription','manual','2026-08-16 09:30:00','','',0,'2026-10-24 16:24:36'),
(71,1,1500,'Health','Cult Gym','UPI','subscription','manual','2026-08-11 09:30:00','','',0,'2026-10-24 16:24:36'),
(72,1,649,'Bills','Netflix','Card','subscription','manual','2026-07-23 09:30:00','','',0,'2026-10-24 16:24:36'),
(73,1,119,'Bills','Spotify','UPI','subscription','manual','2026-07-17 09:30:00','','',0,'2026-10-24 16:24:36'),
(74,1,1500,'Health','Cult Gym','UPI','subscription','manual','2026-07-12 09:30:00','','',0,'2026-10-24 16:24:36'),
(75,2,194.85,'Food','Zomato','UPI','','manual','2026-10-23 13:00:36','','',0,'2026-10-24 16:24:36'),
(76,2,325.56,'Food','Zomato','UPI','','manual','2026-10-16 13:00:36','','',0,'2026-10-24 16:24:36'),
(77,2,121.76,'Food','Zomato','UPI','','manual','2026-10-09 13:00:36','','',0,'2026-10-24 16:24:36'),
(78,2,237.49,'Food','Zomato','UPI','','manual','2026-10-02 13:00:36','','',0,'2026-10-24 16:24:36'),
(79,3,7.38,'Food','Snack Shop','Cash','','manual','2026-10-24 16:00:36','','',0,'2026-10-24 16:24:37'),
(80,3,11.33,'Food','Snack Shop','Cash','','manual','2026-10-21 16:00:36','','',0,'2026-10-24 16:24:37'),
(81,3,10.79,'Food','Snack Shop','Cash','','manual','2026-10-21 16:00:36','','',0,'2026-10-24 16:24:37'),
(82,3,3.58,'Food','Snack Shop','Cash','','manual','2026-10-17 16:00:36','','',0,'2026-10-24 16:24:37'),
(83,3,9.04,'Food','Snack Shop','Cash','','manual','2026-10-16 16:00:36','','',0,'2026-10-24 16:24:37'),
(84,4,1089.34,'Health','Pharmacy','Card','','manual','2026-10-22 10:00:37','','',0,'2026-10-24 16:24:37'),
(85,4,1788.51,'Groceries','BigBasket','Card','','manual','2026-10-24 11:00:37','','',0,'2026-10-24 16:24:37'),
(86,4,1123.18,'Health','Pharmacy','Card','','manual','2026-10-15 10:00:37','','',0,'2026-10-24 16:24:37'),
(87,4,907.04,'Groceries','BigBasket','Card','','manual','2026-10-17 11:00:37','','',0,'2026-10-24 16:24:37'),
(88,4,1253.68,'Health','Pharmacy','Card','','manual','2026-10-08 10:00:37','','',0,'2026-10-24 16:24:37'),
(89,4,1169.44,'Groceries','BigBasket','Card','','manual','2026-10-10 11:00:37','','',0,'2026-10-24 16:24:37'),
(90,4,1130.71,'Health','Pharmacy','Card','','manual','2026-10-01 10:00:37','','',0,'2026-10-24 16:24:37'),
(91,4,1745.04,'Groceries','BigBasket','Card','','manual','2026-10-03 11:00:37','','',0,'2026-10-24 16:24:37'),
(92,4,707.43,'Health','Pharmacy','Card','','manual','2026-09-24 10:00:37','','',0,'2026-10-24 16:24:37'),
(93,4,1003.89,'Groceries','BigBasket','Card','','manual','2026-09-26 11:00:37','','',0,'2026-10-24 16:24:37'),
(94,4,685.63,'Health','Pharmacy','Card','','manual','2026-09-17 10:00:37','','',0,'2026-10-24 16:24:37'),
(95,4,1397.9,'Groceries','BigBasket','Card','','manual','2026-09-19 11:00:37','','',0,'2026-10-24 16:24:37'),
(96,4,817.88,'Health','Pharmacy','Card','','manual','2026-09-10 10:00:37','','',0,'2026-10-24 16:24:37'),
(97,4,1444.35,'Groceries','BigBasket','Card','','manual','2026-09-12 11:00:37','','',0,'2026-10-24 16:24:37'),
(98,4,1174.09,'Health','Pharmacy','Card','','manual','2026-09-03 10:00:37','','',0,'2026-10-24 16:24:37'),
(99,4,1083.24,'Groceries','BigBasket','Card','','manual','2026-09-05 11:00:37','','',0,'2026-10-24 16:24:37'),
(100,4,1107.39,'Health','Pharmacy','Card','','manual','2026-08-27 10:00:37','','',0,'2026-10-24 16:24:37'),
(101,4,1137.59,'Groceries','BigBasket','Card','','manual','2026-08-29 11:00:37','','',0,'2026-10-24 16:24:37'),
(102,4,990.83,'Health','Pharmacy','Card','','manual','2026-08-20 10:00:37','','',0,'2026-10-24 16:24:37'),
(103,4,1714.8,'Groceries','BigBasket','Card','','manual','2026-08-22 11:00:37','','',0,'2026-10-24 16:24:37'),
(104,4,1276.88,'Health','Pharmacy','Card','','manual','2026-08-13 10:00:37','','',0,'2026-10-24 16:24:37'),
(105,4,983.07,'Groceries','BigBasket','Card','','manual','2026-08-15 11:00:37','','',0,'2026-10-24 16:24:37'),
(106,4,938.86,'Health','Pharmacy','Card','','manual','2026-08-06 10:00:37','','',0,'2026-10-24 16:24:37'),
(107,4,1149.01,'Groceries','BigBasket','Card','','manual','2026-08-08 11:00:37','','',0,'2026-10-24 16:24:37'),
(108,4,602.84,'Health','Pharmacy','Card','','manual','2026-07-30 10:00:37','','',0,'2026-10-24 16:24:37'),
(109,4,1594.01,'Groceries','BigBasket','Card','','manual','2026-08-01 11:00:37','','',0,'2026-10-24 16:24:37'),
(110,5,40,'Food','School canteen','Cash','','manual','2026-10-23 13:24:43','','',0,'2026-10-24 16:24:43'),
(111,5,150,'Shopping','Toy shop','Cash','','manual','2026-10-22 13:24:43','','',0,'2026-10-24 16:24:43'),
(112,5,60,'Food','Ice cream','Cash','','manual','2026-10-20 13:24:43','','',0,'2026-10-24 16:24:43'),
(113,5,40,'Food','School canteen','Cash','','manual','2026-10-19 13:24:43','','',0,'2026-10-24 16:24:43'),
(114,5,120,'Entertainment','Comic book','Cash','','manual','2026-10-17 13:24:43','','',0,'2026-10-24 16:24:43'),
(115,5,40,'Food','School canteen','Cash','','manual','2026-10-15 13:24:43','','',0,'2026-10-24 16:24:43'),
(116,5,90,'Shopping','Stationery','Cash','','manual','2026-10-08 13:24:43','','',0,'2026-10-24 16:24:43'),
(117,5,60,'Food','Ice cream','Cash','','manual','2026-09-30 13:24:43','','',0,'2026-10-24 16:24:43');
DROP TABLE IF EXISTS `families`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `families` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `emoji` varchar(10) DEFAULT NULL,
  `invite_code` varchar(12) NOT NULL,
  `monthly_budget` float DEFAULT NULL,
  `currency` varchar(10) DEFAULT NULL,
  `created_by` int(11) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_families_invite_code` (`invite_code`),
  KEY `created_by` (`created_by`),
  KEY `ix_families_id` (`id`),
  CONSTRAINT `families_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

INSERT INTO `families` (`id`, `name`, `emoji`, `invite_code`, `monthly_budget`, `currency`, `created_by`, `created_at`) VALUES (1,'The Demo Family','🏡','DEMO42',0,'INR',1,'2026-10-24 16:24:42');
DROP TABLE IF EXISTS `family_challenges`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `family_challenges` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `family_id` int(11) NOT NULL,
  `kind` varchar(20) NOT NULL,
  `title` varchar(200) DEFAULT NULL,
  `target` float NOT NULL,
  `category` varchar(100) DEFAULT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `created_by` int(11) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `created_by` (`created_by`),
  KEY `ix_family_challenges_family_id` (`family_id`),
  KEY `ix_family_challenges_id` (`id`),
  CONSTRAINT `family_challenges_ibfk_1` FOREIGN KEY (`family_id`) REFERENCES `families` (`id`),
  CONSTRAINT `family_challenges_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

INSERT INTO `family_challenges` (`id`, `family_id`, `kind`, `title`, `target`, `category`, `start_date`, `end_date`, `created_by`, `created_at`) VALUES (1,1,'no_spend_days','No-spend days',12,'','2026-10-22','2026-10-28',1,'2026-10-24 16:24:43'),
(2,1,'log_days','',5,'','2026-10-21','2026-10-27',1,'2026-10-24 16:24:43');
DROP TABLE IF EXISTS `family_kudos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `family_kudos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `family_id` int(11) NOT NULL,
  `from_user` int(11) NOT NULL,
  `to_user` int(11) NOT NULL,
  `emoji` varchar(10) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `from_user` (`from_user`),
  KEY `to_user` (`to_user`),
  KEY `ix_family_kudos_family_id` (`family_id`),
  KEY `ix_family_kudos_id` (`id`),
  CONSTRAINT `family_kudos_ibfk_1` FOREIGN KEY (`family_id`) REFERENCES `families` (`id`),
  CONSTRAINT `family_kudos_ibfk_2` FOREIGN KEY (`from_user`) REFERENCES `users` (`id`),
  CONSTRAINT `family_kudos_ibfk_3` FOREIGN KEY (`to_user`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

INSERT INTO `family_kudos` (`id`, `family_id`, `from_user`, `to_user`, `emoji`, `created_at`) VALUES (1,1,1,2,'👏','2026-10-24 13:24:43'),
(2,1,2,1,'🔥','2026-10-24 13:24:43'),
(3,1,4,3,'🌟','2026-10-24 09:24:43'),
(4,1,1,5,'🏆','2026-10-24 10:24:43'),
(5,1,3,1,'💚','2026-10-24 12:24:43');
DROP TABLE IF EXISTS `family_members`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `family_members` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `family_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `role` varchar(10) DEFAULT NULL,
  `avatar` varchar(10) DEFAULT NULL,
  `share_level` varchar(10) DEFAULT NULL,
  `joined_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `ix_family_members_id` (`id`),
  KEY `ix_family_members_family_id` (`family_id`),
  CONSTRAINT `family_members_ibfk_1` FOREIGN KEY (`family_id`) REFERENCES `families` (`id`),
  CONSTRAINT `family_members_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

INSERT INTO `family_members` (`id`, `family_id`, `user_id`, `role`, `avatar`, `share_level`, `joined_at`) VALUES (1,1,1,'owner','😎','full','2026-09-14 16:24:42'),
(2,1,2,'member','🦊','totals','2026-09-14 16:24:42'),
(3,1,3,'child','🐼','full','2026-09-14 16:24:42'),
(4,1,4,'member','🦁','full','2026-09-14 16:24:42'),
(5,1,5,'child','🧸','full','2026-09-24 16:24:43');
DROP TABLE IF EXISTS `goal_contributions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `goal_contributions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `goal_id` int(11) NOT NULL,
  `amount` float NOT NULL,
  `note` varchar(200) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_goal_contributions_id` (`id`),
  KEY `ix_goal_contributions_goal_id` (`goal_id`),
  CONSTRAINT `goal_contributions_ibfk_1` FOREIGN KEY (`goal_id`) REFERENCES `goals` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

DROP TABLE IF EXISTS `goals`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `goals` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `title` varchar(300) NOT NULL,
  `target_amount` float NOT NULL,
  `saved_amount` float DEFAULT NULL,
  `deadline` datetime NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `ix_goals_id` (`id`),
  CONSTRAINT `goals_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

INSERT INTO `goals` (`id`, `user_id`, `title`, `target_amount`, `saved_amount`, `deadline`, `created_at`) VALUES (1,1,'Buy Laptop',60000,18000,'2027-04-22 16:24:36','2026-10-24 16:24:36'),
(2,3,'New Bike',120,32,'2026-12-23 16:24:36','2026-10-24 16:24:37'),
(3,4,'Home Repairs',50000,21000,'2027-03-23 16:24:37','2026-10-24 16:24:37'),
(4,5,'New bicycle',4000,1800,'2027-01-22 16:24:43','2026-10-24 16:24:43');
DROP TABLE IF EXISTS `interventions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `interventions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `trigger_id` int(11) NOT NULL,
  `intervention_type` varchar(30) NOT NULL,
  `variant` varchar(5) DEFAULT NULL,
  `description` varchar(500) NOT NULL,
  `status` varchar(20) DEFAULT NULL,
  `baseline_avg` float DEFAULT NULL,
  `result_avg` float DEFAULT NULL,
  `effectiveness_pct` float DEFAULT NULL,
  `user_feedback` varchar(10) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `trigger_id` (`trigger_id`),
  KEY `ix_interventions_id` (`id`),
  CONSTRAINT `interventions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `interventions_ibfk_2` FOREIGN KEY (`trigger_id`) REFERENCES `triggers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

DROP TABLE IF EXISTS `triggers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `triggers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `context_key` varchar(100) NOT NULL,
  `category_affected` varchar(100) NOT NULL,
  `description` varchar(500) NOT NULL,
  `evidence_json` text NOT NULL,
  `confidence` float NOT NULL,
  `occurrences` int(11) DEFAULT NULL,
  `last_seen` datetime DEFAULT NULL,
  `first_seen` datetime DEFAULT NULL,
  `active` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `ix_triggers_id` (`id`),
  CONSTRAINT `triggers_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

INSERT INTO `triggers` (`id`, `user_id`, `context_key`, `category_affected`, `description`, `evidence_json`, `confidence`, `occurrences`, `last_seen`, `first_seen`, `active`) VALUES (1,1,'Late Night+Weekday','Food','You tend to spend on Food during late night, weekday periods','[\"10 of 10 similar transactions in this context were \'Food\'\", \"10 occurred after 9 PM\", \"Pattern repeated across 9 distinct week(s)\"]',0.99,10,'2026-10-16 22:44:36','2026-10-24 16:24:36',1),
(2,1,'Evening+Weekend','Transport','You tend to spend on Transport during evening, weekend periods','[\"3 of 3 similar transactions in this context were \'Transport\'\", \"Consistently logged during evening hours\", \"Pattern repeated across 2 distinct week(s)\"]',0.99,3,'2026-10-04 19:10:36','2026-10-24 16:24:36',1),
(3,1,'Evening+Weekday','Transport','You tend to spend on Transport during evening, weekday periods','[\"9 of 11 similar transactions in this context were \'Transport\'\", \"Consistently logged during evening hours\", \"Pattern repeated across 7 distinct week(s)\"]',0.89,9,'2026-10-22 18:27:36','2026-10-24 16:24:36',1),
(4,1,'Late Night+Weekend','Food','You tend to spend on Food during late night, weekend periods','[\"7 of 8 similar transactions in this context were \'Food\'\", \"7 occurred after 9 PM\", \"Pattern repeated across 6 distinct week(s)\"]',0.82,7,'2026-10-24 22:08:36','2026-10-24 16:24:36',1),
(5,1,'Afternoon+Weekday','Groceries','You tend to spend on Groceries during afternoon, weekday periods','[\"12 of 16 similar transactions in this context were \'Groceries\'\", \"Consistently logged during afternoon hours\", \"Pattern repeated across 12 distinct week(s)\"]',0.81,12,'2026-10-22 11:14:36','2026-10-24 16:24:36',1);
DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `monthly_income` float DEFAULT NULL,
  `current_savings` float DEFAULT NULL,
  `age` int(11) DEFAULT NULL,
  `date_of_birth` date DEFAULT NULL,
  `platform_mode` varchar(20) DEFAULT NULL,
  `adult_transition_prompted` tinyint(1) DEFAULT NULL,
  `senior_transition_prompted` tinyint(1) DEFAULT NULL,
  `currency` varchar(10) DEFAULT NULL,
  `base_currency` varchar(10) DEFAULT NULL,
  `language` varchar(10) DEFAULT NULL,
  `theme` varchar(20) DEFAULT NULL,
  `font_scale` float DEFAULT NULL,
  `font_style` varchar(30) DEFAULT NULL,
  `line_spacing` varchar(10) DEFAULT NULL,
  `guardian_confirmed` tinyint(1) DEFAULT NULL,
  `managed_by` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_email` (`email`),
  KEY `ix_users_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `monthly_income`, `current_savings`, `age`, `date_of_birth`, `platform_mode`, `adult_transition_prompted`, `senior_transition_prompted`, `currency`, `base_currency`, `language`, `theme`, `font_scale`, `font_style`, `line_spacing`, `guardian_confirmed`, `managed_by`, `created_at`) VALUES (1,'Demo User','demo@spendsense.app','$2b$12$kZEQTeWNz1VpW0c/PAna2Oul2pqfXVrEZVP3mESloCh10b1LCKeiK',45000,0,NULL,'2002-10-24','adult',0,0,'INR','INR','en','night',1,'default','normal',0,NULL,'2026-10-24 16:24:36'),
(2,'Alex (turned 18)','teen@spendsense.app','$2b$12$1QVFiNCUHblrb0uTaQMiiOzBB7Mbk8iwl.m8H5B889FRMZacvQUUO',8000,1500,NULL,'2008-10-21','teen',0,0,'INR','INR','en','kid',1,'default','normal',0,NULL,'2026-10-24 16:24:36'),
(3,'Sam','kid@spendsense.app','$2b$12$glsyy3d4flk0bs4SzqWPh.m5TFWfn.px9tiAPjAX5pIv0X7A1JeUG',0,32,NULL,'2016-10-24','kid',0,0,'USD','USD','en','kid',1,'default','normal',1,NULL,'2026-10-24 16:24:37'),
(4,'Margaret','senior@spendsense.app','$2b$12$9Fm3eonI4ToHDU6catEOTudp8isv4lX0Ec.DtBBcVGHzpSjdKhbou',32000,210000,NULL,'1958-10-24','senior',0,0,'INR','INR','en','senior',1,'default','normal',0,NULL,'2026-10-24 16:24:37'),
(5,'Aarav','aarav@kids.spendsense.app','$2b$12$v7B558.TkVN9zSM0PzpOb.GAU5dfpIDiaa62z5D0WK5G9GvKSItXm',0,0,8,NULL,'kid',0,0,'INR','INR','en','kid',1,'default','normal',1,1,'2026-10-24 16:24:43');
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

