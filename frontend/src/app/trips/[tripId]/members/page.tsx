import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { getTrip } from "@/lib/trips";
import { getInvitations, getMembers } from "@/lib/collaboration";
import TripHeader from "../../trip-header";
import InviteForm from "../../invite-form";
import ConfirmAction from "../../confirm-action";
import {
  leaveTrip,
  createInvitation,
  removeMember,
  revokeInvitation,
} from "../../member-actions";

export const metadata: Metadata = { title: "旅伴與邀請 | TripSync" };

export default async function MembersPage({
  params,
}: {
  params: Promise<{ tripId: string }>;
}) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const { tripId } = await params;
  const trip = await getTrip(tripId);
  const owner = trip.owner_id === user.id;
  const [members, invitations] = await Promise.all([
    getMembers(tripId),
    owner ? getInvitations(tripId) : Promise.resolve([]),
  ]);
  return (
    <>
      <TripHeader trip={trip} active="members" />
      <div className="grid items-start gap-8 lg:grid-cols-[1.2fr_1fr]">
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-xl font-bold">
            一起出發的旅伴{" "}
            <span className="ml-2 text-sm font-normal text-zinc-500">
              {members.length} 人
            </span>
          </h2>
          <p className="mt-2 text-sm leading-6 text-zinc-500">
            所有旅伴都能安排每日活動；旅程資料與成員由建立者管理。
          </p>
          <ul className="mt-6 divide-y divide-zinc-100 dark:divide-zinc-800">
            {members.map((member) => (
              <li
                key={member.user_id}
                className="flex flex-wrap items-center gap-3 py-4"
              >
                <span
                  aria-hidden="true"
                  className="flex size-10 shrink-0 items-center justify-center rounded-full bg-teal-50 font-semibold text-teal-800 dark:bg-teal-950 dark:text-teal-200"
                >
                  {member.username.slice(0, 1).toUpperCase()}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="break-words font-semibold">
                    {member.username}
                    {member.user_id === user.id && (
                      <span className="ml-2 text-xs font-normal text-zinc-500">
                        你
                      </span>
                    )}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {member.is_owner ? "旅程建立者" : "共同規劃的旅伴"}
                  </p>
                </div>
                {owner && !member.is_owner && (
                  <ConfirmAction
                    action={removeMember.bind(null, trip.id, member.user_id)}
                    label="移除成員"
                    confirmation={`移除 ${member.username} 後，對方將無法再存取旅程；已建立的活動會保留。`}
                  />
                )}
              </li>
            ))}
          </ul>
          {!owner && (
            <div className="mt-6 border-t border-zinc-100 pt-4 dark:border-zinc-800">
              <ConfirmAction
                action={leaveTrip.bind(null, trip.id)}
                label="退出旅程"
                confirmation="退出後將無法再查看或修改這趟旅程，已建立的活動會保留。"
              />
            </div>
          )}
        </section>
        {owner ? (
          <section
            id="invite"
            className="rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900"
          >
            <h2 className="text-xl font-bold">邀請旅伴加入</h2>
            <p className="mb-5 mt-3 text-sm leading-6 text-zinc-500">
              每個連結限一位新成員使用，七天後到期。只分享給信任的人；對方加入後即可共同編輯每日行程。
            </p>
            <InviteForm createAction={createInvitation.bind(null, trip.id)} />
            <h3 className="mt-8 text-sm font-semibold">最近的邀請</h3>
            {invitations.length === 0 ? (
              <p className="mt-3 text-sm text-zinc-500">尚未建立邀請連結。</p>
            ) : (
              <ul className="mt-3 divide-y divide-zinc-100 dark:divide-zinc-800">
                {invitations.map((invitation) => {
                  const status = {
                    revoked: "已撤銷",
                    used: "已使用",
                    expired: "已到期",
                    pending: "等待加入",
                  }[invitation.status];
                  return (
                    <li key={invitation.id} className="py-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium">
                            邀請 #{invitation.id} · {status}
                          </p>
                          <p className="mt-1 text-xs text-zinc-500">
                            到期：
                            {new Intl.DateTimeFormat("zh-TW", {
                              dateStyle: "medium",
                              timeStyle: "short",
                              timeZone: "Asia/Taipei",
                            }).format(new Date(invitation.expires_at))}
                          </p>
                        </div>
                        {status === "等待加入" && (
                          <ConfirmAction
                            action={revokeInvitation.bind(
                              null,
                              trip.id,
                              invitation.id,
                            )}
                            label="撤銷邀請"
                            confirmation="撤銷後，這個連結將無法再讓新成員加入。"
                          />
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        ) : (
          <aside className="rounded-2xl bg-teal-50 p-6 text-sm leading-7 text-teal-900 dark:bg-teal-950/40 dark:text-teal-200">
            想邀請更多朋友？請旅程建立者提供新的邀請連結。
          </aside>
        )}
      </div>
    </>
  );
}
