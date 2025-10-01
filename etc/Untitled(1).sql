CREATE TABLE `users` (
  `id` integer PRIMARY KEY,
  `username` text,
  `password` text
);

CREATE TABLE `words` (
  `id` integer PRIMARY KEY,
  `userID` integer NOT NULL,
  `word` text,
  `translation` text,
  `definition` text,
  `origin` text,
  `date` date,
  `pass` integer,
  `passWithHelp` integer,
  `fail` integer,
  `failWithHelp` integer
);

ALTER TABLE `words` ADD CONSTRAINT `user_posts` FOREIGN KEY (`userID`) REFERENCES `users` (`id`);
