"""Observed completion records and read-only per-Topic summaries."""
import json
from pathlib import Path
from . import topic_service as topics

FIELDS = ('kind','topic','ticket','level','started_at','finished_at','outcome','test_runs',
          'review_rounds','findings','repair_rounds','needs_user_count','command_errors',
          'reviewer_provenance','tests_configured')

def provenance(reviews):
    sources = {r.get('result', {}).get('reviewer', {}).get('provenance') for r in reviews}
    sources.discard(None)
    if not sources:
        return None
    return 'mixed' if len(sources) > 1 or 'mixed' in sources else next(iter(sources))

def summarize(repo, topic=None):
    repo = topics.safe_repo(repo)
    if topic is not None:
        topics.topic_path(repo, topic)
    path = repo / '.agent/metrics.jsonl'
    records = []
    for line in path.read_text().splitlines() if path.exists() else []:
        try:
            value = json.loads(line)
        except ValueError as exc:
            raise topics.TopicError('metrics.jsonl 包含无效 JSON') from exc
        if not isinstance(value, dict) or not isinstance(value.get('topic'), str):
            raise topics.TopicError('metrics.jsonl 记录缺少 topic')
        if topic is None or value['topic'] == topic:
            records.append(value)
    groups = {}
    for name in sorted({r['topic'] for r in records}):
        rows = [r for r in records if r['topic'] == name]
        counts = {}
        for key in ('test_runs','review_rounds','repair_rounds','needs_user_count','command_errors'):
            known = [r[key] for r in rows if isinstance(r.get(key), int)]
            counts[key] = sum(known) if len(known) == len(rows) else None
        sources = [{'result': {'reviewer': {'provenance': r.get('reviewer_provenance')}}} for r in rows]
        groups[name] = {'records': len(rows), 'counts': counts,
                        'reviewer_provenance': provenance(sources),
                        'outcomes': {o: sum(r.get('outcome') == o for r in rows)
                                     for o in ('complete','accepted','abandoned')}}
    return {'records': records, 'topics': groups}

def command_error_count(repo, topic, started_at=None, ticket=None):
    path = Path(repo) / '.agent/command-errors.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    return sum(row['topic'] == topic and (started_at is None or row['at'] >= started_at)
               and (ticket is None or row.get('ticket') == ticket) for row in rows)

def record_command_error(argv, parsed=None):
    """Record only attributable failures in an already configured v2 project."""
    def option(name, default=None):
        if parsed is not None:
            return getattr(parsed, name[2:].replace('-', '_'), default)
        for argument in reversed(argv):
            if argument.startswith(name + '='):
                return argument.split('=',1)[1]
        if name in argv:
            index = argv.index(name)
            return argv[index + 1] if index + 1 < len(argv) else default
        return default
    try:
        repo = topics.safe_repo(option('--repo', '.'))
        topics.read_config(repo)
        ticket = option('--ticket')
        topic = option('--topic') or (ticket.rsplit('-',1)[0] if ticket else None)
        if topic is None:
            topic = topics.select_topic(repo, None)
        path = topics.topic_path(repo, topic)
        if not path.is_dir() or not (path / topics.STATE_FILE).is_file():
            return
        if ticket is None:
            from .ticket_implementation import records
            active = [identifier for identifier, (_, value) in records(repo,topic).items()
                      if value['status'] in {'implementing','needs-user'}]
            ticket = active[0] if len(active) == 1 else None
        row = {'topic': topic, 'ticket': ticket, 'at': topics.now()}
        with (repo / '.agent/command-errors.jsonl').open('a') as stream:
            stream.write(json.dumps(row, ensure_ascii=False)+'\n')
    except (topics.TopicError, OSError, ValueError):
        # Invalid/migrating projects remain zero-write; telemetry cannot replace
        # the original validation error or guess an ambiguous Topic.
        return

def topic_observations(repo, topic, value, config):
    """Read available observations without inventing reviews for a document Topic."""
    root = topics.topic_path(repo, topic)
    if value.get('level') is None:
        return {}
    if value['level'] == 'quick':
        return {'test_runs': value.get('test_runs',0), 'reviewer_provenance':'self',
                'tests_configured': bool(topics.full_tests(config))}
    # Ticket observations have their own records; Topic counters describe the
    # branch object and must not import child rounds or reviewer provenance.
    units = []
    branch = root/'branch-review.json'
    if branch.exists():
        unit = json.loads(branch.read_text())
        tests = root/'topic-tests.json'
        unit['tests'] = json.loads(tests.read_text()).get('tests',[]) if tests.exists() else []
        units.append(unit)
    reviews = [r for u in units for r in u.get('reviews',[])]
    findings = [f for r in reviews for f in r.get('result',{}).get('findings',[])]
    return {'test_runs': sum(len({t.get('run_id',t.get('finished_at')) for t in u.get('tests',[])}) for u in units),
            'review_rounds': len(reviews), 'findings': {s:sum(f.get('severity')==s for f in findings) for s in ('blocking','advisory')},
            'repair_rounds': sum(bool(r.get('repair')) for r in reviews),
            'needs_user_count': sum(u.get('needs_user_count',0) for u in units),
            'reviewer_provenance': provenance(reviews), 'tests_configured':bool(topics.full_tests(config))}
