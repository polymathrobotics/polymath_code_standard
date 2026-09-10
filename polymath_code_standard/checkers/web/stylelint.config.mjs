// SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
// SPDX-License-Identifier: Apache-2.0
//
// Polymath baseline Stylelint configuration.
// Stylelint rejects a config whose rules live only in overrides, so the CSS baseline stays at the root.

export default {
  extends: ["stylelint-config-standard"],
  overrides: [
    {
      files: ["**/*.scss"],
      extends: ["stylelint-config-standard-scss"],
    },
  ],
};
