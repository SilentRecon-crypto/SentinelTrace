import { useAsync } from "@/hooks/useAsync";
import { getUserProfile } from "@/services/userApi";
import { PageHeader } from "@/components/ui/PageHeader";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { formatDate } from "@/utils/format";

export function UserProfile() {
  const { data: profile, loading } = useAsync(getUserProfile, []);

  return (
    <div className="animate-fade-in">
      <PageHeader eyebrow="Account" title="Profile" description="Your account details for the SentinelTrace User Portal." />
      {loading || !profile ? (
        <SkeletonBlock className="h-56" />
      ) : (
        <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[color:var(--color-signal-dim)] text-[16px] font-semibold text-[color:var(--color-signal)]">
              {profile.name[0]}
            </div>
            <div>
              <div className="text-[15px] font-semibold text-[color:var(--color-text-primary)]">{profile.name}</div>
              <div className="text-[11.5px] text-[color:var(--color-text-tertiary)]">Member since {formatDate(profile.memberSince)}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3.5 py-2.5">
              <div className="text-[10px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Email</div>
              <div className="mt-1 text-[12.5px] font-medium text-[color:var(--color-text-primary)]">{profile.email}</div>
            </div>
            <div className="rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3.5 py-2.5">
              <div className="text-[10px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Phone</div>
              <div className="mt-1 text-[12.5px] font-medium text-[color:var(--color-text-primary)]">{profile.phone}</div>
            </div>
          </div>
          <p className="mt-4 text-[11px] text-[color:var(--color-text-tertiary)]">Profile editing isn't available in this demo environment.</p>
        </div>
      )}
    </div>
  );
}
