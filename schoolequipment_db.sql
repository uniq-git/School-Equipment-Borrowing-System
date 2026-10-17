-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Oct 17, 2026 at 10:14 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `school_equipment_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `borrow_requests`
--

CREATE TABLE `borrow_requests` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `equipment_id` int(11) NOT NULL,
  `quantity` int(11) NOT NULL DEFAULT 1,
  `status` enum('Pending','Approved','Denied','Returned','Cancelled') NOT NULL DEFAULT 'Pending',
  `request_date` datetime DEFAULT current_timestamp(),
  `due_date` date DEFAULT NULL,
  `approved_by` int(11) DEFAULT NULL,
  `approved_at` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `returned_at` datetime DEFAULT NULL,
  `returned_by` int(11) DEFAULT NULL,
  `returned_quantity` int(11) DEFAULT NULL,
  `return_condition` enum('New','Good','Fair','Needs Repair','Damaged','Lost') DEFAULT NULL,
  `return_notes` varchar(255) DEFAULT NULL,
  `overdue_reminder_sent_at` datetime DEFAULT NULL,
  `purpose` varchar(255) DEFAULT NULL,
  `deny_reason` varchar(255) DEFAULT NULL,
  `return_requested_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `borrow_requests`
--

INSERT INTO `borrow_requests` (`id`, `user_id`, `equipment_id`, `quantity`, `status`, `request_date`, `due_date`, `approved_by`, `approved_at`, `created_at`, `returned_at`, `returned_by`, `returned_quantity`, `return_condition`, `return_notes`, `overdue_reminder_sent_at`, `purpose`, `deny_reason`, `return_requested_at`) VALUES
(2, 3, 5, 4, 'Returned', '2026-09-14 10:43:41', '2026-09-20', 2, '2026-09-14 12:35:53', '2026-09-14 02:43:41', '2026-10-04 02:08:02', 3, 4, 'Good', NULL, NULL, NULL, NULL, NULL),
(3, 3, 9, 1, 'Returned', '2026-10-01 14:20:11', '2026-10-05', 2, '2026-10-02 23:35:18', '2026-10-01 06:20:11', '2026-10-07 13:35:59', 3, 1, 'Damaged', 'nasira po yung handler ng hammer', '2026-10-06 14:51:51', NULL, NULL, NULL),
(4, 3, 8, 4, 'Returned', '2026-10-06 15:13:37', '2026-10-07', 2, '2026-10-06 15:14:36', '2026-10-06 07:13:37', '2026-10-07 13:45:42', 2, 4, 'Damaged', '2 is damage and 2 is good condition, nabagsak', NULL, NULL, NULL, NULL),
(5, 176, 8, 1, 'Returned', '2026-10-06 15:15:29', '2026-10-10', 2, '2026-10-06 15:15:44', '2026-10-06 07:15:29', '2026-10-07 13:53:52', 2, 1, 'Good', NULL, NULL, NULL, NULL, NULL),
(6, 3, 9, 1, 'Approved', '2026-10-07 13:58:44', '2026-10-08', 2, '2026-10-07 13:58:53', '2026-10-07 05:58:44', NULL, NULL, NULL, NULL, NULL, '2026-10-14 02:08:05', NULL, NULL, '2026-10-14 04:02:03');

-- --------------------------------------------------------

--
-- Table structure for table `email_verifications`
--

CREATE TABLE `email_verifications` (
  `id` int(11) NOT NULL,
  `email` varchar(150) NOT NULL,
  `code` varchar(6) NOT NULL,
  `is_verified` tinyint(1) NOT NULL DEFAULT 0,
  `expires_at` datetime NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `attempts` int(11) NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `email_verifications`
--

INSERT INTO `email_verifications` (`id`, `email`, `code`, `is_verified`, `expires_at`, `created_at`, `attempts`) VALUES
(7, 'ricjohn62@gmail.com', '829987', 1, '2026-09-04 20:13:08', '2026-09-04 12:03:08', 0),
(20, 'admin123@gmail.com', '006734', 0, '2026-09-13 23:14:46', '2026-09-13 15:04:46', 0),
(28, 'admin@icct.edu.ph', '399075', 0, '2026-10-06 15:04:04', '2026-10-06 06:54:04', 0),
(29, 'iccthelpdesk.edu.ph@gmail.com', '976775', 1, '2026-10-07 13:42:59', '2026-10-07 05:32:48', 0);

-- --------------------------------------------------------

--
-- Table structure for table `equipment`
--

CREATE TABLE `equipment` (
  `id` int(11) NOT NULL,
  `name` varchar(150) NOT NULL,
  `category` varchar(100) NOT NULL,
  `quantity` int(11) NOT NULL DEFAULT 1,
  `condition_status` enum('New','Good','Fair','Needs Repair') NOT NULL DEFAULT 'Good',
  `photo_path` varchar(255) DEFAULT NULL,
  `added_by` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `under_repair` int(11) NOT NULL DEFAULT 0,
  `is_deleted` tinyint(1) NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `equipment`
--

INSERT INTO `equipment` (`id`, `name`, `category`, `quantity`, `condition_status`, `photo_path`, `added_by`, `created_at`, `under_repair`, `is_deleted`) VALUES
(4, 'Microphone', 'Audio Equipment', 2, 'Good', 'd5c10c62212d4a4f964d04eb8024c065.png', 2, '2026-09-11 19:37:51', 0, 0),
(5, 'VGA Cable', 'Cables & Adapters', 10, 'Good', 'a1cebdbad6294fb4b3f721f384be472f.png', 2, '2026-09-11 19:38:06', 0, 0),
(6, 'Digital Camera', 'Camera', 2, 'New', '87b9ecdfa8cb41758deae385d08e2c73.png', 2, '2026-10-01 06:06:49', 0, 0),
(7, '2-in-1 Laptop', 'Laptop', 1, 'New', 'b2261ada763e441c94d31e017b6884a9.png', 2, '2026-10-01 06:07:00', 0, 0),
(8, 'Portable Projector', 'Projector', 5, 'Fair', '7068e2d2a0c646d390cb2516332d2379.png', 2, '2026-10-01 06:07:19', 4, 0),
(9, 'Hammer', 'Tools', 2, 'Needs Repair', 'bd1cf9ff446c44009fd32d2bc2295491.png', 2, '2026-10-01 06:07:38', 1, 0);

-- --------------------------------------------------------

--
-- Table structure for table `equipment_categories`
--

CREATE TABLE `equipment_categories` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `equipment_categories`
--

INSERT INTO `equipment_categories` (`id`, `name`, `created_at`) VALUES
(1, 'Camera', '2026-09-06 14:38:10'),
(2, 'Laptop', '2026-09-06 14:38:10'),
(3, 'Projector', '2026-09-06 14:38:10'),
(4, 'Audio Equipment', '2026-09-06 14:38:10'),
(5, 'Cables & Adapters', '2026-09-06 14:38:10'),
(6, 'Sports Equipment', '2026-09-06 14:38:10'),
(7, 'Tools', '2026-09-06 14:38:10'),
(8, 'Other', '2026-09-06 14:38:10');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `full_name` varchar(150) NOT NULL,
  `student_number` varchar(20) NOT NULL,
  `email` varchar(150) NOT NULL,
  `contact_number` varchar(20) DEFAULT NULL,
  `password` varchar(255) NOT NULL,
  `role` enum('Admin','Student','Teacher','Staff') NOT NULL DEFAULT 'Student',
  `email_verified` tinyint(1) NOT NULL DEFAULT 0,
  `status` enum('active','inactive') NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `failed_logins` int(11) NOT NULL DEFAULT 0,
  `locked_until` datetime DEFAULT NULL,
  `must_change_password` tinyint(1) NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `full_name`, `student_number`, `email`, `contact_number`, `password`, `role`, `email_verified`, `status`, `created_at`, `failed_logins`, `locked_until`, `must_change_password`) VALUES
(2, 'System Administrator', 'AD000000001', 'admin@icct.edu.ph', NULL, '$2b$12$J9EPNy6JOh6uBkPBdnC6L.ALZqLfa2kvOM1Wrlo/B3ZuCrYcFaHUu', 'Admin', 1, 'active', '2026-09-04 11:35:34', 0, NULL, 0),
(3, 'Johnric Suaiso', 'CA202409678', 'johnric.suaiso3@gmail.com', NULL, '$2b$12$IXWK6IYUArVpj2nByWT0POrJqpr7.EAEPqdu2/v59bvIdZHp3CfZ6', 'Student', 1, 'active', '2026-09-04 11:59:26', 0, NULL, 0),
(64, 'Staff', 'SF000000001', 'staff@gmail.com', NULL, '$2b$12$uYA1YGqU7Pf/yAb1BImLQu25pKIjEalKaPV0UZg2/X6Af.Vq.wuNG', 'Staff', 1, 'active', '2026-09-11 17:18:40', 0, NULL, 0),
(176, 'Louie Sebastian', 'TC202400001', 'teacher@gmail.com', NULL, '$2b$12$S9mbH4xda6xz5Y1KHjw2xeUw3vgSd2LQH82jEKsB9np9pfaSX.naK', 'Teacher', 1, 'active', '2026-10-06 07:11:59', 0, NULL, 0),
(177, 'Admin John', 'AD000000002', 'iccthelpdesk.edu.ph@gmail.com', NULL, '$2b$12$HWbvWO2nme3zS7gwwAY.Qen9UFBx1sVQZulgOEjy3CS/pzCqtTYbS', 'Admin', 1, 'active', '2026-10-07 05:30:47', 0, NULL, 1);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `borrow_requests`
--
ALTER TABLE `borrow_requests`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `equipment_id` (`equipment_id`),
  ADD KEY `approved_by` (`approved_by`),
  ADD KEY `returned_by` (`returned_by`);

--
-- Indexes for table `email_verifications`
--
ALTER TABLE `email_verifications`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `equipment`
--
ALTER TABLE `equipment`
  ADD PRIMARY KEY (`id`),
  ADD KEY `added_by` (`added_by`);

--
-- Indexes for table `equipment_categories`
--
ALTER TABLE `equipment_categories`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `student_number` (`student_number`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `borrow_requests`
--
ALTER TABLE `borrow_requests`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `email_verifications`
--
ALTER TABLE `email_verifications`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=31;

--
-- AUTO_INCREMENT for table `equipment`
--
ALTER TABLE `equipment`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT for table `equipment_categories`
--
ALTER TABLE `equipment_categories`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1435;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=178;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `borrow_requests`
--
ALTER TABLE `borrow_requests`
  ADD CONSTRAINT `borrow_requests_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `borrow_requests_ibfk_2` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `borrow_requests_ibfk_3` FOREIGN KEY (`approved_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `borrow_requests_ibfk_4` FOREIGN KEY (`returned_by`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Constraints for table `equipment`
--
ALTER TABLE `equipment`
  ADD CONSTRAINT `equipment_ibfk_1` FOREIGN KEY (`added_by`) REFERENCES `users` (`id`) ON DELETE SET NULL;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
