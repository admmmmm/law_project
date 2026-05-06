from .ner import one_shot_ner_paragraph, one_shot_ner_output
from ...utils.llm_utils import convert_format_to_template

ner_conditioned_re_system = """你的任务是根据段落和命名实体列表抽取中文事实三元组。
请重点抽取侦查、司法、资金和人员关系，不要抽取空泛关系。

优先使用以下关系类型：
- 任职于、职务为、负责、批准、指派、安排、介入；
- 请托、收受、行贿、转账、取现、存入、赔偿；
- 立案、拘留、释放、调解、撤案、结案、侦查；
- 亲属、同事、上下级、经营、控制账户；
- 明知、隐瞒、规避、倒签、补录。

要求：
- 每个三元组至少包含一个命名实体，最好包含两个命名实体。
- 代词必须还原为具体人名或机构名。
- 关系必须用中文短语。
- 只能依据当前段落，不得把示例中的实体或关系带入新段落。
- 只返回 JSON，格式为 {"triples": [[subject, relation, object], ...]}。

"""


ner_conditioned_re_frame = """Convert the paragraph into a JSON dict, it has a named entity list and a triple list.
Paragraph:
```
{passage}
```

{named_entity_json}
"""


ner_conditioned_re_input = ner_conditioned_re_frame.format(passage=one_shot_ner_paragraph, named_entity_json=one_shot_ner_output)


ner_conditioned_re_output = """{"triples": [
            ["杨周武", "职务为", "同乐派出所副所长"],
            ["王静", "请托", "杨周武"],
            ["杨周武", "安排介入调解", "刘力飚"],
            ["刘力飚", "身份为", "非办案民警"],
            ["王静", "通过", "何晓初"],
            ["何晓初", "收受", "3万元"],
            ["刘力飚", "促成和解", "2008年9月6日"],
            ["和解", "赔偿金额", "11万元"]
    ]
}
"""


prompt_template = [
    {"role": "system", "content": ner_conditioned_re_system},
    {"role": "user", "content": ner_conditioned_re_input},
    {"role": "assistant", "content": ner_conditioned_re_output},
    {"role": "user", "content": convert_format_to_template(original_string=ner_conditioned_re_frame, placeholder_mapping=None, static_values=None)}
]
