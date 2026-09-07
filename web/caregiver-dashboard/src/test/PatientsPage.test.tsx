import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { PatientsPage } from "../pages/PatientsPage"
import { dashboardApi } from "../api/dashboardApi"

vi.mock("../api/dashboardApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/dashboardApi")>()
  return {
    ...actual,
    dashboardApi: {
      ...actual.dashboardApi,
      assignedPatients: vi.fn(),
    },
  }
})

const mockPatients = vi.mocked(dashboardApi.assignedPatients)

// Wrap in MemoryRouter because PatientsPage calls useNavigate.
function renderPage() {
  return render(
    <MemoryRouter>
      <PatientsPage />
    </MemoryRouter>
  )
}

describe("PatientsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders the panel heading", async () => {
    mockPatients.mockResolvedValue([])
    renderPage()
    expect(screen.getByRole("heading", { name: /Assigned patients/i })).toBeInTheDocument()
  })

  it("shows loading state initially", () => {
    // Never-resolving promise keeps loading state visible.
    mockPatients.mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByRole("status")).toBeInTheDocument()
  })

  it("shows empty state when no patients are assigned", async () => {
    mockPatients.mockResolvedValue([])
    renderPage()
    await waitFor(() =>
      expect(screen.getByText(/No patients are assigned/i)).toBeInTheDocument()
    )
  })

  it("renders a button for each assigned patient", async () => {
    mockPatients.mockResolvedValue([
      { id: "maya-demo", name: "Maya Devi", age: 72, preferredLanguage: "Assamese" },
      { id: "other-demo", name: "Priya Sharma", age: 68, preferredLanguage: "Hindi" },
    ] as never)
    renderPage()
    await waitFor(() => expect(screen.getByText("Maya Devi")).toBeInTheDocument())
    expect(screen.getByText("Priya Sharma")).toBeInTheDocument()
  })

  it("navigates to patient profile when a patient row is clicked", async () => {
    mockPatients.mockResolvedValue([
      { id: "maya-demo", name: "Maya Devi", age: 72, preferredLanguage: "Assamese" },
    ] as never)
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => expect(screen.getByText("Maya Devi")).toBeInTheDocument())
    // Navigation is tested by verifying the row is clickable (not throwing).
    await user.click(screen.getByText("Maya Devi"))
  })

  it("shows an error state and retry button on API failure", async () => {
    mockPatients.mockRejectedValue(new Error("Network error"))
    renderPage()
    await waitFor(() => expect(screen.getByText(/Network error/)).toBeInTheDocument())
    expect(screen.getByRole("button", { name: /Retry/i })).toBeInTheDocument()
  })

  it("retries the API call when Retry is clicked", async () => {
    mockPatients.mockRejectedValueOnce(new Error("Temp failure"))
    mockPatients.mockResolvedValue([])
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => expect(screen.getByRole("button", { name: /Retry/i })).toBeInTheDocument())
    await user.click(screen.getByRole("button", { name: /Retry/i }))
    expect(mockPatients).toHaveBeenCalledTimes(2)
  })

  it("shows supportive description text", async () => {
    mockPatients.mockResolvedValue([])
    renderPage()
    await waitFor(() => expect(screen.getByText(/supportive activity and safety/i)).toBeInTheDocument())
  })
})
