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
    for ticket in report.get('tickets', []):
        if isinstance(ticket, str):
            lines.append('Ticket：'+ticket)
            continue
        line=f"Ticket {ticket['ticket']}：{LABELS.get(ticket['status'], '状态待核实')}"
        if ticket.get('stop_reason'):
            line+='；原因：'+LABELS.get(ticket['stop_reason'],ticket['stop_reason'])
        if ticket.get('recovery_error'):
            line+='；恢复检查：'+ticket['recovery_error']
        lines.append(line)
    batch=report.get('batch_status')
    if isinstance(batch,dict):lines.append(f"批次 {batch['batch']}：{batch['state']}")
    elif isinstance(report.get('batch'),str):lines.append('批次：'+report['batch'])
    reason=report.get('stop_reason') or (report.get('branch_review') or {}).get('stop_reason')
    if reason:
        for code,label in LABELS.items():
            reason=reason.replace(code,label)
        lines.append('原因：'+reason)
    for decision in report.get('decisions_needed',[]):
        subject=(decision.get('finding') or {}).get('summary', '方案存在待决事项')
        if decision.get('ticket'):
            subject='Ticket '+decision['ticket']+'：'+LABELS.get(decision.get('reason'),'审查停止，需要用户决定')
        lines.append(subject+'；'+decision['decision'])
    for item in report.get('unverified',[]):
        lines.append('未验证：'+(item.get('command','')+'；'+item.get('note','') if isinstance(item,dict) else str(item)))
    if report.get('next_command'):lines.append('下一步：'+report['next_command'])
    return '\n'.join(lines)
