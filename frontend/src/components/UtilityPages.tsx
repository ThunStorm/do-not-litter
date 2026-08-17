import { CheckSquare, Folder, UserRound } from 'lucide-react'

import { PageHeader } from './AppShell'

export function SourcesPage() { return <UtilityPage title="来源" icon={Folder} detail="原始链接、快照、附件与 Claim/Evidence 关系将在这里统一审计。" /> }
export function TodosPage() { return <UtilityPage title="待办" icon={CheckSquare} detail="身份确认、POI 歧义和即将截止事项会集中出现在这里。" /> }
export function ProfilePage() { return <UtilityPage title="我的" icon={UserRound} detail="个人档案默认只保存在 Mac mini，本地规则计算优先于外部模型。" /> }

function UtilityPage({ title, icon: Icon, detail }: { title: string; icon: typeof Folder; detail: string }) {
  return <div className="page-frame utility-page"><PageHeader title={title} /><section><Icon /><h2>{title}</h2><p>{detail}</p></section></div>
}
