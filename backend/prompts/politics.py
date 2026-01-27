POLITICS_OPERATIONAL_DEFINITION = """
Politics label spec (operational)
Label name: POLITICS

Core criterion:
Assign POLITICS if the primary focus of the article is power, governance, or collective decision-making carried out by political institutions/actors, or the processes that select/control them.
“Primary focus” = the main story would still be the same if you removed all non-political details; politics is not just a cameo.

Include if ANY of these is the main subject:
A) Government & institutions (domestic)
- Executive actions: cabinet decisions, ministries, agencies, regulators acting in official capacity
- Legislature: bills, votes, committees, parliamentary negotiations
- Public administration: government programs, budgets, procurement policy (not company-specific business news)
- Local government: mayors, councils, regional authorities, public service governance

B) Elections & party politics
- Elections, campaigns, polling, debates, candidate selection, coalition talks
- Party leadership, internal party conflicts when politically consequential
- Political strategy, messaging, endorsements

C) Public policy (substance + debate)
- Policy proposals, reforms, regulation, taxation, welfare, healthcare policy, education policy, climate policy, etc.
- **Implementation of new legislation** (National or EU Directives) impacting society or business sectors.
- Political conflict over policy (who supports/opposes; parliamentary dynamics; veto threats)

D) Political accountability & legitimacy
- Resignations, impeachments, no-confidence votes
- Ethics, corruption, conflicts of interest when tied to governance (not just criminal detail)
- Constitutional crises, institutional clashes, rule-of-law disputes

E) International politics & diplomacy
- Treaties, summits, sanctions, foreign policy statements
- Diplomatic incidents, recognition disputes, geopolitical negotiations

F) Civil liberties & rights as political contestation
- Protests, civil society actions, strikes when framed around policy/government power
- Major court rulings when they reshape governance or political rights (elections, constitutional issues)

Exclude (unless politics is clearly primary):
1) Crime / courts: If it’s mainly “who did what, evidence, trial details,” label CRIME/LAW, not POLITICS. Exception: if the case directly affects governance.
2) Business / economy: Market moves, company earnings, mergers → BUSINESS. Exception: sanctions, antitrust, budgets, or **new regulations/laws** being implemented → POLITICS.
3) Disasters / weather / accidents: If the focus is the event itself → DISASTER. Exception: political accountability/policy response dominates.
4) Culture / celebrity: Politicians as celebrities (personal life) → ENTERTAINMENT unless tied to office, campaign, or legitimacy.
5) Sports: Sports story with a politician quote is still SPORTS unless it becomes policy.

Decision rules:
Rule P1 — Actor × Action (strong signal): If article contains political actors/institutions AND governance actions, assign POLITICS.
Rule P2 — Elections/party process (strong signal): If the main content concerns elections, campaigns, polling, coalitions, party leadership, assign POLITICS.
Rule P3 — Policy conflict frame (medium signal): If the article is structured as policy debate, assign POLITICS.
Rule P4 — International statecraft (strong signal): If it involves states/IGOs and diplomatic/military/economic coercion instruments, assign POLITICS.
Rule P5 — “Mention-only” veto: If political entity is mentioned but not central, do NOT assign POLITICS.
"""
