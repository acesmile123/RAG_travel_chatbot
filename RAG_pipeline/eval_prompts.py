from unsloth import FastLanguageModel

EVAL_PROMPTS = [
    "Giới thiệu về Đà Nẵng",
    "Nên đi Đà Nẵng mùa nào?",
    "Ăn gì ở Đà Nẵng?",
    "Di chuyển từ sân bay Đà Nẵng vào trung tâm thế nào?",
]

def qualitative_eval(model, tokenizer):
    FastLanguageModel.for_inference(model)
    for q in EVAL_PROMPTS:
        prompt = f"<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n"
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        out = model.generate(**inputs, max_new_tokens=256)
        print(q)
        print(tokenizer.decode(out[0], skip_special_tokens=True))
        print("="*50)
