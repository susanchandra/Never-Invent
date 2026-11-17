// NeverInvent Frontend Client Application

let currentCandidateId = null;
let currentCandidateProfile = null;
let currentProposal = null;

// Tab Switching
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    
    btn.classList.add("active");
    const target = btn.getAttribute("data-tab");
    document.getElementById(target).classList.add("active");

    if (target === "tab-audit") {
      loadAudits();
    }
  });
});

function switchTab(tabId) {
  const btn = document.querySelector(`[data-tab="${tabId}"]`);
  if (btn) btn.click();
}

// 1. Ingestion / Upload
document.getElementById("loadSampleBtn").addEventListener("click", async () => {
  const sampleResume = `Alice Smith
alice.smith@example.com | (555) 123-4567

Skills
Python, PyTorch, Kubernetes, AWS, FAISS, Docker, Spark

Work Experience
Google - Senior Machine Learning Engineer
Jan 2021 - Present
- Designed search ranking models improving relevance by 18%.
- Scaled inference service handling 500ms requests.

Meta - Machine Learning Engineer
Jan 2019 - Dec 2020
- Built data processing pipelines using Python and Spark.

Education
Stanford University
B.S. in Computer Science
2015 - 2019
`;

  try {
    const formData = new FormData();
    formData.append("raw_text_input", sampleResume);
    const resp = await fetch("/api/resume/upload", { method: "POST", body: formData });
    const data = await resp.json();
    currentCandidateId = data.candidate_id;
    currentCandidateProfile = data.profile;
    renderProfile(data.profile);
    loadJobs();
  } catch (err) {
    alert("Failed to load sample resume: " + err);
  }
});

document.getElementById("uploadFileBtn").addEventListener("click", async () => {
  const fileInput = document.getElementById("resumeFileInput");
  if (!fileInput.files.length) {
    alert("Please select a PDF or TXT file first.");
    return;
  }
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const resp = await fetch("/api/resume/upload", { method: "POST", body: formData });
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    currentCandidateId = data.candidate_id;
    currentCandidateProfile = data.profile;
    renderProfile(data.profile);
    loadJobs();
  } catch (err) {
    alert("Upload failed: " + err);
  }
});

function renderProfile(profile) {
  document.getElementById("profileContainer").style.display = "block";
  document.getElementById("profileName").innerText = profile.candidate_name || "Candidate";
  document.getElementById("profileContact").innerText = `${profile.email || ""} | ${profile.phone || ""}`;

  // Skills
  const skillsDiv = document.getElementById("profileSkills");
  skillsDiv.innerHTML = profile.skills.map(s => `<span class="tag">${s.name}</span>`).join("");

  // Metrics
  const metricsDiv = document.getElementById("profileMetrics");
  metricsDiv.innerHTML = profile.metrics.map(m => `
    <div style="font-size: 0.85rem; margin-bottom: 0.3rem;">
      <strong style="color: var(--accent-blue);">${m.quantity}${m.unit || ""}</strong> — ${m.raw_metric_text}
    </div>
  `).join("") || "<span style='color: var(--text-muted);'>No explicit metrics</span>";

  // Experience
  const expDiv = document.getElementById("profileExperience");
  expDiv.innerHTML = profile.experience.map(e => `
    <div style="margin-bottom: 0.8rem; border-left: 2px solid var(--border); padding-left: 0.8rem;">
      <div style="font-weight: 600;">${e.company} — <span style="color: var(--accent-blue);">${e.title || "Role"}</span></div>
      <div style="font-size: 0.8rem; color: var(--text-muted);">${e.start_date || ""} to ${e.end_date || ""} (${e.duration_months || "?"} mos)</div>
      <ul style="font-size: 0.85rem; margin-left: 1.2rem; color: var(--text-secondary);">
        ${(e.responsibilities || []).map(r => `<li>${r}</li>`).join("")}
      </ul>
    </div>
  `).join("");
}

// 2. Jobs Listing & Search
async function loadJobs() {
  try {
    const resp = await fetch("/api/jobs");
    const data = await resp.json();
    renderJobs(data.jobs || []);
    populateJobSelect(data.jobs || []);
  } catch (err) {
    console.error("Failed to load jobs", err);
  }
}

document.getElementById("searchJobsBtn").addEventListener("click", async () => {
  const query = document.getElementById("jobSearchQuery").value;
  const method = document.getElementById("searchMethodSelect").value;
  try {
    const resp = await fetch("/api/jobs/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, method, top_k: 6 })
    });
    const data = await resp.json();
    renderJobSearchResults(data.results || []);
  } catch (err) {
    alert("Search error: " + err);
  }
});

function renderJobs(jobs) {
  const list = document.getElementById("jobsList");
  list.innerHTML = jobs.map(j => `
    <div class="card" style="background: #090d16; margin-bottom: 0.75rem;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <div style="font-weight: 700; color: #fff;">${j.title}</div>
          <div style="color: var(--text-muted); font-size: 0.85rem;">${j.company} | Min Exp: ${j.min_years_experience || 0} yrs</div>
        </div>
        <button class="btn btn-secondary" onclick="inspectJobMatch('${j.job_id}')">Match Breakdown</button>
      </div>
    </div>
  `).join("");
}

function renderJobSearchResults(results) {
  const list = document.getElementById("jobsList");
  list.innerHTML = results.map(r => `
    <div class="card" style="background: #090d16; margin-bottom: 0.75rem;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <div style="font-weight: 700; color: #fff;">${r.title || r.job_id}</div>
          <div style="color: var(--text-muted); font-size: 0.85rem;">Rank #${r.rank} | Method: ${r.method} | Retrieval Score: ${r.score.toFixed(4)}</div>
        </div>
        <button class="btn btn-secondary" onclick="inspectJobMatch('${r.job_id}')">Match Breakdown</button>
      </div>
    </div>
  `).join("");
}

function populateJobSelect(jobs) {
  const select = document.getElementById("proposalJobSelect");
  select.innerHTML = jobs.map(j => `<option value="${j.job_id}">${j.title} (${j.company})</option>`).join("");
}

window.inspectJobMatch = async function(jobId) {
  if (!currentCandidateId) {
    alert("Please upload or load a candidate profile first in Step 1.");
    switchTab("tab-upload");
    return;
  }
  try {
    const resp = await fetch("/api/jobs/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_id: currentCandidateId, job_id: jobId })
    });
    const data = await resp.json();
    renderMatchBreakdown(data.breakdown);
  } catch (err) {
    alert("Match breakdown failed: " + err);
  }
};

function renderMatchBreakdown(breakdown) {
  const container = document.getElementById("matchBreakdownContainer");
  container.style.display = "block";
  document.getElementById("matchSummary").innerHTML = `
    <strong>Target:</strong> ${breakdown.job_title} at ${breakdown.company}<br>
    <strong>Grounded Match Score:</strong> ${(breakdown.grounded_match_score * 100).toFixed(1)}% 
    (70% required coverage + 30% preferred coverage)
  `;

  document.getElementById("reqSkillsList").innerHTML = breakdown.required_skills_match.map(s => `
    <div style="margin-bottom: 0.4rem; font-size: 0.85rem;">
      <span class="verdict-badge ${s.status === 'SUPPORTED' ? 'supported' : 'unsupported'}" style="font-size: 0.7rem; padding: 0.1rem 0.4rem;">
        ${s.status}
      </span>
      <strong>${s.skill_name}</strong>
      ${s.supporting_evidence ? `<span style="color: var(--text-muted);"> (anchor: "${s.supporting_evidence.evidence_text}")</span>` : ''}
    </div>
  `).join("") || "None";

  document.getElementById("prefSkillsList").innerHTML = breakdown.preferred_skills_match.map(s => `
    <div style="margin-bottom: 0.4rem; font-size: 0.85rem;">
      <span class="verdict-badge ${s.status === 'SUPPORTED' ? 'supported' : 'ambiguous'}" style="font-size: 0.7rem; padding: 0.1rem 0.4rem;">
        ${s.status}
      </span>
      <strong>${s.skill_name}</strong>
      ${s.supporting_evidence ? `<span style="color: var(--text-muted);"> (anchor: "${s.supporting_evidence.evidence_text}")</span>` : ''}
    </div>
  `).join("") || "None";

  const db = breakdown.dealbreaker_result;
  document.getElementById("dealbreakerStatus").innerHTML = `
    <span class="verdict-badge ${db.passed ? 'supported' : 'unsupported'}">
      Dealbreakers: ${db.passed ? 'PASSED' : 'FAILED'}
    </span>
    ${db.failed_reasons.length ? `<div style="color: #f87171; font-size: 0.85rem; margin-top: 0.3rem;">${db.failed_reasons.join("<br>")}</div>` : ''}
  `;
}

// 3. Generation & Verification
document.getElementById("generateProposalBtn").addEventListener("click", async () => {
  if (!currentCandidateId) {
    alert("Please upload or load a candidate profile first in Step 1.");
    switchTab("tab-upload");
    return;
  }

  const jobId = document.getElementById("proposalJobSelect").value;
  const generationType = document.getElementById("proposalTypeSelect").value;
  const mode = document.getElementById("proposalModeSelect").value;
  const provider = document.getElementById("proposalProviderSelect").value;
  const targetBullet = document.getElementById("targetBulletInput").value;

  try {
    const resp = await fetch("/api/verify/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        candidate_id: currentCandidateId,
        job_id: jobId,
        generation_type: generationType,
        mode: mode,
        provider: provider,
        target_bullet: targetBullet
      })
    });
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    currentProposal = data.proposal;
    renderVerificationScreen(data.proposal);
    switchTab("tab-verify");
  } catch (err) {
    alert("Generation / Verification failed: " + err);
  }
});

function renderVerificationScreen(proposal) {
  // Status Badge
  const statusEl = document.getElementById("proposalStatusBadge");
  let badgeClass = "supported";
  if (proposal.status === "CONTAINS_UNSUPPORTED") badgeClass = "unsupported";
  else if (proposal.status === "CONTAINS_AMBIGUOUS") badgeClass = "ambiguous";

  statusEl.innerHTML = `
    <span class="verdict-badge ${badgeClass}" style="font-size: 0.95rem;">
      ${proposal.status.replace(/_/g, " ")}
    </span>
  `;

  // Diff
  document.getElementById("diffOriginalBox").innerText = proposal.original_text || "(None)";
  
  // Highlight diffs in proposed box
  let proposedHtml = proposal.proposed_text;
  if (proposal.diff_highlights && proposal.diff_highlights.length) {
    for (const d of proposal.diff_highlights) {
      if (d.kind === "changed_metric") {
        proposedHtml = proposedHtml.replace(
          d.value,
          `<span class="diff-changed-metric">${d.value} (changed from ${d.original_value || 'orig'})</span>`
        );
      }
    }
  }
  document.getElementById("diffProposedBox").innerHTML = proposedHtml;

  // Render Claims
  const claimsDiv = document.getElementById("claimsList");
  if (!proposal.verification_results || !proposal.verification_results.length) {
    claimsDiv.innerHTML = "<p style='color: var(--text-muted);'>No atomic claims extracted.</p>";
  } else {
    claimsDiv.innerHTML = proposal.verification_results.map(r => {
      const v = r.final_verdict;
      const vClass = v.toLowerCase();
      let evidenceSnippet = "";
      if (r.matched_evidence && r.matched_evidence.length) {
        evidenceSnippet = `<strong>Matched Evidence:</strong> "${r.matched_evidence[0].evidence_text}" (Field: ${r.matched_evidence[0].profile_field})`;
      } else if (r.contradicting_evidence && r.contradicting_evidence.length) {
        evidenceSnippet = `<strong style="color: #f87171;">Contradicting Evidence:</strong> "${r.contradicting_evidence[0].evidence_text}"`;
      } else {
        evidenceSnippet = "<em>No direct candidate evidence found in resume. Escalate for human verification.</em>";
      }

      return `
        <div class="claim-card ${vClass}-card">
          <div class="claim-header">
            <div>
              <span class="verdict-badge ${vClass}">${v}</span>
              <span class="tag">${r.claim.claim_type}</span>
              <span style="font-size: 0.8rem; color: var(--text-muted);">Strategy: ${r.primary_strategy} (${r.latency_ms.toFixed(2)} ms)</span>
            </div>
          </div>
          <div class="claim-text">Claim: "${r.claim.original_claim_text}"</div>
          <div style="font-size: 0.85rem; color: var(--text-secondary);">${r.rationale}</div>
          <div class="claim-evidence">${evidenceSnippet}</div>
        </div>
      `;
    }).join("");
  }

  // Pre-fill editable text box
  document.getElementById("candidateEditableText").value = proposal.proposed_text;
}

// 4. Re-Verify Manual Edit
document.getElementById("reverifyEditBtn").addEventListener("click", async () => {
  if (!currentProposal || !currentCandidateId) {
    alert("No active proposal to reverify.");
    return;
  }
  const editedText = document.getElementById("candidateEditableText").value;
  try {
    const resp = await fetch("/api/verify/reverify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        proposal_id: currentProposal.proposal_id,
        candidate_id: currentCandidateId,
        edited_text: editedText
      })
    });
    const data = await resp.json();
    currentProposal = data.proposal;
    renderVerificationScreen(data.proposal);
    alert("Manual edit re-verified! Verdicts updated.");
  } catch (err) {
    alert("Re-verification error: " + err);
  }
});

// 5. Approval & Rejection
document.getElementById("approveProposalBtn").addEventListener("click", () => recordDecision("APPROVED"));
document.getElementById("rejectProposalBtn").addEventListener("click", () => recordDecision("REJECTED"));

async function recordDecision(decisionType) {
  if (!currentProposal) {
    alert("No active proposal to record.");
    return;
  }

  const finalText = document.getElementById("candidateEditableText").value;
  const isEdited = (finalText.trim() !== currentProposal.proposed_text.trim());
  const actualDecision = (decisionType === "APPROVED" && isEdited) ? "MANUALLY_EDITED_APPROVED" : decisionType;

  try {
    const resp = await fetch("/api/approve/decision", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        proposal_id: currentProposal.proposal_id,
        decision: actualDecision,
        final_text: finalText,
        notes: `Recorded via NeverInvent verification screen (${actualDecision})`
      })
    });
    if (!resp.ok) throw new Error(await resp.text());
    alert(`Decision recorded successfully: ${actualDecision}`);
    switchTab("tab-audit");
  } catch (err) {
    alert("Failed to record decision: " + err);
  }
}

// 6. Audit Trail Loading
async function loadAudits() {
  try {
    const resp = await fetch("/api/approve/audits");
    const data = await resp.json();
    const tbody = document.getElementById("auditTableBody");
    if (!data.audits || !data.audits.length) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No decisions recorded yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = data.audits.map(a => `
      <tr>
        <td style="color: var(--text-muted); font-size: 0.8rem;">${a.timestamp ? new Date(a.timestamp).toLocaleString() : '-'}</td>
        <td style="font-family: monospace; font-size: 0.85rem;">${a.proposal_id.substring(0, 8)}...</td>
        <td>
          <span class="verdict-badge ${a.decision.includes('APPROVED') ? 'supported' : 'unsupported'}" style="font-size: 0.75rem;">
            ${a.decision}
          </span>
        </td>
        <td style="max-width: 400px; word-break: break-word;">${a.final_text}</td>
        <td style="color: var(--text-muted); font-size: 0.85rem;">${a.decision_notes || '-'}</td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to load audits", err);
  }
}

// Auto-seed initial sample on page load
window.addEventListener("DOMContentLoaded", () => {
  document.getElementById("loadSampleBtn").click();
});
