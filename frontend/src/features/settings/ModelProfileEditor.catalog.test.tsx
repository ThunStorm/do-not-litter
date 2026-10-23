import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import { ModelProfileEditor } from "./SettingsPage";

vi.mock("../../lib/api", () => ({ api: { modelCatalog: vi.fn(), modelCredentialStatus: vi.fn() } }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
function openDraft() {
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><ModelProfileEditor /></QueryClientProvider>);
  fireEvent.click(screen.getByRole("button", { name: "自定义" }));
  fireEvent.click(screen.getByRole("option", { name: "LocalAiMux（本机路由）" }));
}

describe("new LocalAiMux model", () => {
  it("automatically reads the directory with server-side shared credentials and edits in place", async () => {
    vi.mocked(api.modelCredentialStatus).mockResolvedValue({ api_key_saved: true, conflict: false });
    vi.mocked(api.modelCatalog).mockResolvedValue({ models: [{ id: "qoder/Kimi-K3" }], sampled_at: "fixture" });
    openDraft();
    await screen.findByText("已读取 1 个模型；选择后请保存。");
    expect(api.modelCatalog).toHaveBeenCalledWith(undefined, expect.objectContaining({ api_key: "", provider: "LocalAiMux" }));
    expect(screen.queryByText("目录凭据")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "codebuddy/hy3" }));
    fireEvent.click(screen.getByRole("option", { name: "qoder/Kimi-K3" }));
    fireEvent.click(screen.getByRole("button", { name: "手动填写模型名" }));
    expect(screen.getByLabelText("模型名")).toHaveValue("qoder/Kimi-K3");
    fireEvent.change(screen.getByLabelText("模型名"), { target: { value: "custom/model" } });
    fireEvent.click(screen.getByRole("button", { name: "选择模型" }));
    expect(screen.getByRole("button", { name: "custom/model" })).toBeInTheDocument();
  });
  it("prompts for a missing key without fetching an anonymous catalog", async () => {
    vi.mocked(api.modelCredentialStatus).mockResolvedValue({ api_key_saved: false, conflict: false });
    openDraft();
    await screen.findByText("请先在下方填写 LocalAiMux API Key。");
    expect(screen.getByRole("button", { name: "刷新模型列表" })).toBeDisabled();
    expect(api.modelCatalog).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("API Key（LocalAiMux 共享凭据）"), { target: { value: "typed-key" } });
    await waitFor(() => expect(screen.getByRole("button", { name: "刷新模型列表" })).toBeEnabled());
  });
});
