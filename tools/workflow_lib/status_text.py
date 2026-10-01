"""Human status rendering; machine JSON keeps its stable state codes."""
LABELS={'pending':'待开始','active':'进行中','archived':'已归档','open':'实施中',
        'reviewing':'审查中','needs-user':'需要用户裁决','closed':'已收口',
        'implementing':'实施中','ready-for-agent':'可开始实施','revalidated':'已重新核实',
        'complete':'已提交','blocked-by-design':'需要用户决定方案','inconclusive':'证据不足，需要用户决定'}


def render(report):
    state=report.get('state',report.get('status'))
    state=LABELS.get(state,state if state in LABELS.values() else '状态待核实')
    if report.get('decisions_needed'):state='需要用户裁决'
    lines=[f"工作 {report.get('topic','')}：{state}"]
    if report.get('ticket'):lines.append('Ticket：'+report['ticket'])
    batch=report.get('batch_status')
    if isinstance(batch,dict):lines.append(f"批次 {batch['batch']}：{batch['state']}")
    elif isinstance(report.get('batch'),str):lines.append('批次：'+report['batch'])
    reason=report.get('stop_reason') or (report.get('branch_review') or {}).get('stop_reason')
    if reason:
        for code,label in LABELS.items():
            if '-' in code:reason=reason.replace(code,label)
        lines.append('原因：'+reason)
    for decision in report.get('decisions_needed',[]):
        lines.append((decision.get('finding') or {}).get('summary','方案存在待决事项')+'；'+decision['decision'])
    for item in report.get('unverified',[]):
        lines.append('未验证：'+(item.get('command','')+'；'+item.get('note','') if isinstance(item,dict) else str(item)))
    if report.get('next_command'):lines.append('下一步：'+report['next_command'])
    return '\n'.join(lines)
