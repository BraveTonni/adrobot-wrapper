"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { CampaignCreateForm } from "./CampaignCreateForm";
import { CampaignEditor } from "./CampaignEditor";
import { CampaignPicker } from "./CampaignPicker";
import { useCampaignWorkspace } from "./useCampaignWorkspace";

type Section = "create" | "edit";

export function CampaignWorkspace() {
  const [section, setSection] = useState<Section>("create");
  const workspace = useCampaignWorkspace();

  function changeSection(nextSection: Section) {
    workspace.setError("");
    setSection(nextSection);
  }

  return (
    <AppShell
      activeSection={section}
      title={section === "create" ? "Новая кампания" : "Управление офферами"}
      onSectionChange={changeSection}
    >
      <header className="title-row">
        <div>
          <p className="eyebrow">Кампании / {section === "create" ? "Создание" : "Редактор"}</p>
          <h1>{section === "create" ? "Создать кампанию" : "Редактор кампаний"}</h1>
          <p className="subtitle">
            {section === "create"
              ? "Настройте гео и целевой оффер — потоки будут созданы автоматически."
              : "Выберите кампанию и управляйте офферами в её потоках."}
          </p>
        </div>
      </header>

      <nav className="tabs" aria-label="Разделы кампаний">
        <button
          className={`tab ${section === "create" ? "active" : ""}`}
          type="button"
          aria-current={section === "create" ? "page" : undefined}
          onClick={() => changeSection("create")}
        >
          Создание
        </button>
        <button
          className={`tab ${section === "edit" ? "active" : ""}`}
          type="button"
          aria-current={section === "edit" ? "page" : undefined}
          onClick={() => changeSection("edit")}
        >
          Редактор
        </button>
      </nav>

      {section === "create" ? (
        <CampaignCreateForm
          form={workspace.form}
          references={workspace.references}
          offers={workspace.offers}
          isLoading={workspace.isLoading}
          isRefreshing={workspace.isRefreshing}
          isSaving={workspace.isSaving}
          creationBlocked={workspace.creationBlocked}
          onChange={workspace.setForm}
          onRefresh={workspace.refreshCatalog}
          onRestart={workspace.restartCreation}
          onSubmit={workspace.createCampaign}
        />
      ) : (
        <>
          <CampaignPicker
            campaigns={workspace.campaigns}
            search={workspace.search}
            selectedId={workspace.campaign?.id}
            isSaving={workspace.isSaving}
            onSearch={workspace.setSearch}
            onSelect={workspace.selectCampaign}
          />
          {workspace.campaign && (
            <CampaignEditor
              campaign={workspace.campaign}
              offers={workspace.offers}
              isSaving={workspace.isSaving}
              onOfferChange={workspace.changeOffer}
              onOfferRestore={workspace.restoreOffer}
              onStreamPush={(streamId) =>
                workspace.updateStreamDraft(streamId, "push")
              }
              onStreamCancel={(streamId) =>
                workspace.updateStreamDraft(streamId, "cancel")
              }
            />
          )}
        </>
      )}

      {workspace.error && (
        <p className="error" role="alert">{workspace.error}</p>
      )}
    </AppShell>
  );
}
