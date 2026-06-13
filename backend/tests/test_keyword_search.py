from app.core.keyword_search import KeywordSearch


def test_keyword_search_ranks_chinese_term_match_first():
    search = KeywordSearch(
        documents=[
            "员工年假按入职年限计算，满一年享有五天年假。",
            "报销需要提交发票和付款凭证。",
            "薪酬发放日期为每月最后一个工作日。",
        ],
        ids=["annual_leave", "expense", "payroll"],
    )

    results = search.search("年假 天数", top_k=2)

    assert [result.id for result in results] == ["annual_leave"]
    assert results[0].rank == 1
    assert results[0].score > 0


def test_keyword_search_uses_jieba_tokenization_for_unspaced_chinese_text():
    search = KeywordSearch(
        documents=[
            "公司提供补充医疗保险和年度体检。",
            "员工可以申请远程办公。",
        ],
        ids=["benefits", "remote_work"],
    )

    results = search.search("医疗保险", top_k=1)

    assert [result.id for result in results] == ["benefits"]


def test_keyword_search_keeps_metadata_and_limits_top_k():
    search = KeywordSearch(
        documents=[
            "招聘流程包括简历筛选和面试。",
            "面试结果会在三个工作日内反馈。",
            "试用期绩效评估由直属经理完成。",
        ],
        ids=["recruiting", "interview", "probation"],
        metadatas=[
            {"page": 1},
            {"page": 2},
            {"page": 3},
        ],
    )

    results = search.search("面试", top_k=1)

    assert len(results) == 1
    assert results[0].id in {"recruiting", "interview"}
    assert results[0].metadata["page"] in {1, 2}


def test_keyword_search_returns_empty_list_for_empty_inputs_or_no_match():
    empty_search = KeywordSearch([])
    search = KeywordSearch(["年假政策", "报销政策"])

    assert empty_search.search("年假") == []
    assert search.search("不存在的词") == []
    assert search.search("   ") == []


def test_keyword_search_returns_empty_when_all_documents_are_blank():
    search = KeywordSearch(
        documents=["", "   "],
        ids=["blank_1", "blank_2"],
    )

    assert search.search("年假") == []
