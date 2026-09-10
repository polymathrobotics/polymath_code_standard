// SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
// SPDX-License-Identifier: Apache-2.0

export interface BannerProps {
  label: string;
}

export function Banner({ label }: BannerProps) {
  return <p className="banner">{label}</p>;
}
