// SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
// SPDX-License-Identifier: Apache-2.0

export interface Greeting {
  message: string;
}

export function greet(name: string): Greeting {
  return { message: `Hello, ${name}` };
}
