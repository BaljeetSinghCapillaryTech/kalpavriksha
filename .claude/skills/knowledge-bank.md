# Knowledge Bank

> Populate this file before running the AIDLC pipeline.
> Add any context, answers, decisions, or domain knowledge that BA might need.
> This reduces back-and-forth questions during the BA phase.
> Content here is treated as human-provided answers — BA will use it directly.
> Clear and re-populate for each new epic/story.

---

NOTE: Refer the below pointers for few of your open questions and architectural decisions, do not assume anything, if confused ask the human ASAP.

1. All the REST APIs CRUDs + Maker-Checker should be added in this Repo: /Users/baljeetsingh/IdeaProjects/intouch-api-v3
2. All the thrift calls (existing + new[if needed]) will be residing in this Repo: /Users/baljeetsingh/IdeaProjects/emf-parent
3. Subscription Programs are partner programs only... we have one thrift already implemented and working fine in existing logic which is written in emf-parent here: PointsEngineRuleConfigThriftImpl: public PartnerProgramInfo createOrUpdatePartnerProgram(PartnerProgramInfo partnerProgramInfo, int programId,
4. There will be only CRUD BE implementation only with all end-to-end validations along with Maker-Checker -> Auditing, simulation will be a future scope
5. Maker-Checker Approval/Rejection etc Authorization per user level will be handled from UI end not by us (Backend).
6. Our new Maker-Checker should be a generic logic as in future other entities like: Tiers, Benefits also needs the Maker-Checker and current UnifiedPromotion's Maker-Checker is too coupled and written specifically for it only.
7. You can refer UnifiedPromotion for the REST APIs CRUDs from /Users/baljeetsingh/IdeaProjects/intouch-api-v3 for Subscription Programs (use Mongo for subscription program metadata and other infos like UnifiedPromotion and only save final data in MySQL existing tables like warehouse.partner_programs etc...)
8. Refer this path for all the types of thrift repos: /Users/baljeetsingh/IdeaProjects/thrifts
9. And the benefits which will be created later can currently be added in the benefits entity and subscription programs can have benefit id as a reference and mapping.
10. program is a parent entity, in a program you can have multiple subscription programs and Subscription to Program is a 1-1 mapping means a subscription program can only be there for a single program not for other programs.
11. Refer /Users/baljeetsingh/IdeaProjects/cc-stack-crm repo for all MySQL databases, tables, schema, indexes etc.
