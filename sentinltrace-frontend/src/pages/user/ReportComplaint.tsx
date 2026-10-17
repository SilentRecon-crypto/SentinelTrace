import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Send } from "lucide-react";
import { submitComplaint } from "@/services/userApi";
import { useAuth } from "@/hooks/useAuth";
import { PageHeader } from "@/components/ui/PageHeader";
import { userPath } from "@/routes";
import type { UserComplaint } from "@/types";

const COMPLAINT_TYPES = ["UPI Fraud", "Fake Investment App", "Card Skimming", "Job Scam", "Phishing", "Online Shopping Fraud", "Social Media Fraud", "Other"];

export function ReportComplaint() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState<UserComplaint | null>(null);
  const [form, setForm] = useState({
    complaintType: COMPLAINT_TYPES[0],
    incidentDate: "",
    amount: "",
    description: "",
    referenceInfo: "",
    contactEmail: user?.handle.includes("@") ? user.handle : "",
    contactPhone: "",
  });

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    const result = await submitComplaint({
      complaintType: form.complaintType,
      incidentDate: form.incidentDate,
      amount: Number(form.amount) || 0,
      description: form.description,
      referenceInfo: form.referenceInfo || undefined,
      contactEmail: form.contactEmail,
      contactPhone: form.contactPhone || undefined,
    });
    setSubmitting(false);
    setSubmitted(result);
  }

  if (submitted) {
    return (
      <div className="animate-fade-in flex flex-col items-center gap-3 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] px-6 py-14 text-center">
        <CheckCircle2 className="h-8 w-8 text-[color:var(--color-low)]" strokeWidth={1.5} />
        <h2 className="text-[16px] font-semibold text-[color:var(--color-text-primary)]">Complaint submitted</h2>
        <p className="max-w-sm text-[12.5px] text-[color:var(--color-text-secondary)]">
          Your complaint <span className="mono-id font-medium text-[color:var(--color-text-primary)]">{submitted.id}</span> has been received and is queued for review.
        </p>
        <div className="mt-2 flex gap-2">
          <button
            onClick={() => navigate(userPath(`/track?complaint=${submitted.id}`))}
            className="rounded-sm bg-[color:var(--color-signal)] px-4 py-2 text-[12.5px] font-semibold text-[#04191c] hover:opacity-90"
          >
            Track this complaint
          </button>
          <button
            onClick={() => navigate(userPath("/complaints"))}
            className="rounded-sm border border-[color:var(--color-border-strong)] px-4 py-2 text-[12.5px] font-medium text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-signal)] hover:text-[color:var(--color-signal)]"
          >
            View my complaints
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Report" title="Report Cybercrime" description="Submit the details below. You'll receive a complaint ID you can use to track its status." />

      <form onSubmit={handleSubmit} className="space-y-4 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1.5 block text-[11.5px] font-medium text-[color:var(--color-text-secondary)]">Complaint Type</label>
            <select
              value={form.complaintType}
              onChange={(e) => update("complaintType", e.target.value)}
              className="h-10 w-full rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 text-[13px] text-[color:var(--color-text-primary)] outline-none focus:border-[color:var(--color-signal)]"
            >
              {COMPLAINT_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-[11.5px] font-medium text-[color:var(--color-text-secondary)]">Incident Date</label>
            <input
              type="date"
              required
              value={form.incidentDate}
              onChange={(e) => update("incidentDate", e.target.value)}
              className="h-10 w-full rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 text-[13px] text-[color:var(--color-text-primary)] outline-none focus:border-[color:var(--color-signal)]"
            />
          </div>
        </div>

        <div>
          <label className="mb-1.5 block text-[11.5px] font-medium text-[color:var(--color-text-secondary)]">Amount Involved (INR)</label>
          <input
            type="number"
            min={0}
            required
            value={form.amount}
            onChange={(e) => update("amount", e.target.value)}
            placeholder="0"
            className="h-10 w-full rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 text-[13px] text-[color:var(--color-text-primary)] outline-none placeholder:text-[color:var(--color-text-tertiary)] focus:border-[color:var(--color-signal)]"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-[11.5px] font-medium text-[color:var(--color-text-secondary)]">Description</label>
          <textarea
            required
            rows={4}
            value={form.description}
            onChange={(e) => update("description", e.target.value)}
            placeholder="Describe what happened, in as much detail as you can."
            className="w-full rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2 text-[13px] text-[color:var(--color-text-primary)] outline-none placeholder:text-[color:var(--color-text-tertiary)] focus:border-[color:var(--color-signal)]"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-[11.5px] font-medium text-[color:var(--color-text-secondary)]">Transaction / Reference Information (optional)</label>
          <input
            value={form.referenceInfo}
            onChange={(e) => update("referenceInfo", e.target.value)}
            placeholder="UPI reference, transaction ID, screenshot description, etc."
            className="h-10 w-full rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 text-[13px] text-[color:var(--color-text-primary)] outline-none placeholder:text-[color:var(--color-text-tertiary)] focus:border-[color:var(--color-signal)]"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1.5 block text-[11.5px] font-medium text-[color:var(--color-text-secondary)]">Contact Email</label>
            <input
              type="email"
              required
              value={form.contactEmail}
              onChange={(e) => update("contactEmail", e.target.value)}
              placeholder="you@example.com"
              className="h-10 w-full rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 text-[13px] text-[color:var(--color-text-primary)] outline-none placeholder:text-[color:var(--color-text-tertiary)] focus:border-[color:var(--color-signal)]"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-[11.5px] font-medium text-[color:var(--color-text-secondary)]">Contact Phone (optional)</label>
            <input
              value={form.contactPhone}
              onChange={(e) => update("contactPhone", e.target.value)}
              placeholder="+91"
              className="h-10 w-full rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 text-[13px] text-[color:var(--color-text-primary)] outline-none placeholder:text-[color:var(--color-text-tertiary)] focus:border-[color:var(--color-signal)]"
            />
          </div>
        </div>

        <p className="text-[10.5px] text-[color:var(--color-text-tertiary)]">
          Only information necessary to process your complaint is collected. This is a demo environment — submissions are not sent to any real authority.
        </p>

        <button
          type="submit"
          disabled={submitting}
          className="flex items-center gap-2 rounded-sm bg-[color:var(--color-signal)] px-5 py-2.5 text-[13px] font-semibold text-[#04191c] transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          <Send className="h-4 w-4" strokeWidth={1.75} /> {submitting ? "Submitting…" : "Submit Complaint"}
        </button>
      </form>
    </div>
  );
}
