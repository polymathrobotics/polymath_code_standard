// SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
// SPDX-License-Identifier: Apache-2.0

const path = require("path");

module.exports = function resolveFixture(name) {
  return path.join(__dirname, name);
};
