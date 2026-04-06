import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/services/attendance", () => ({
  getAttendanceRules: vi.fn().mockResolvedValue({
    tolerance_minutes: 5,
    auto_break_after_hours: 6,
    auto_break_minutes: 30,
    cross_day_shift_cutoff_hour: 6,
    late_early_penalty_hours: "0.25",
  }),
  listMyShifts: vi.fn().mockResolvedValue([]),
  rotateAttendanceQr: vi.fn().mockResolvedValue({ token: "tok", expires_at: "" }),
  attendanceCheckIn: vi.fn(),
  attendanceCheckOut: vi.fn(),
}));

vi.mock("@/utils/feedback", () => ({
  notifyError: vi.fn().mockReturnValue("error"),
}));

import AttendanceView from "./AttendanceView.vue";
import { useAuthStore } from "@/stores/auth";

function mountWith(roles: string[]) {
  const pinia = createPinia();
  setActivePinia(pinia);
  const auth = useAuthStore();
  auth.$patch({
    user: {
      id: 1,
      store_id: 101,
      username: "testuser",
      display_name: "Test User",
      roles,
    },
    initialized: true,
    loading: false,
  });
  return mount(AttendanceView, { global: { plugins: [pinia] } });
}

describe("AttendanceView role gating", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows QR rotation controls for administrator", () => {
    const wrapper = mountWith(["administrator"]);
    expect(wrapper.text()).toContain("Rotate QR Token");
    expect(wrapper.text()).toContain("Start Auto-Rotation");
  });

  it("shows QR rotation controls for store_manager", () => {
    const wrapper = mountWith(["store_manager"]);
    expect(wrapper.text()).toContain("Rotate QR Token");
    expect(wrapper.text()).toContain("Start Auto-Rotation");
  });

  it("hides QR rotation controls for employee", () => {
    const wrapper = mountWith(["employee"]);
    expect(wrapper.text()).not.toContain("Rotate QR Token");
    expect(wrapper.text()).not.toContain("Start Auto-Rotation");
  });

  it("hides QR rotation controls for cashier", () => {
    const wrapper = mountWith(["cashier"]);
    expect(wrapper.text()).not.toContain("Rotate QR Token");
    expect(wrapper.text()).not.toContain("Start Auto-Rotation");
  });

  it("still shows check-in/out sections for employee", () => {
    const wrapper = mountWith(["employee"]);
    expect(wrapper.text()).toContain("Check In");
    expect(wrapper.text()).toContain("Check Out");
    expect(wrapper.text()).toContain("Recent Shifts");
  });
});
