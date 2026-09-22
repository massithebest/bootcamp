import { setStubUserId } from "@/lib/knowledge-user";
import { PERMISSION_APPROVE, PERMISSION_WRITE, type Me } from "@/types/knowledge";

const permissionText = (me: Me) => [me.permissions.includes(PERMISSION_WRITE) && "작성", me.permissions.includes(PERMISSION_APPROVE) && "승인"].filter(Boolean).join("·") || "조회만";

/**
 * 현재 작업 사용자. 인증 연동 전(stub)에는 선택기를 보여주되 실제 인증이 아님을 밝히고,
 * 인증이 연결되면(mode 가 stub 가 아니면) 선택기 없이 이름과 권한만 표시한다.
 */
export function UserSwitcher({ me }: { me: Me }) {
  if (me.mode !== "stub") return <p className="text-ui text-ink-2">{me.name} · {permissionText(me)}</p>;
  return <div className="space-y-1 sm:text-right">
    <label className="flex items-center gap-2 whitespace-nowrap text-ui text-ink-2 sm:justify-end">작업 사용자
      <select aria-label="작업 사용자" className="rounded border border-line-strong bg-canvas px-2.5 py-1.5 text-ui text-ink focus:outline-none focus:ring-2 focus:ring-accent" value={me.id} onChange={e => setStubUserId(e.target.value)}>
        {me.stub_users.map(user => <option key={user.id} value={user.id}>{user.name}</option>)}
      </select>
      <span className="shrink-0 text-2xs text-ink-3">{permissionText(me)}</span>
    </label>
    <p className="text-2xs text-ink-3">인증 연동 전 임시 선택입니다. 작성자·승인자를 구분해 기록할 뿐 보안 인증이 아닙니다.</p>
  </div>;
}
