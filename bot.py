import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

TOPIC, METRIC, QUESTION, RESULT = range(4)

with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

async def start(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    await update.message.reply_text(
        f"Привет, {user.first_name}, я бот, который может оценить этичность Вашего ИИ-решения. "
        "Выберите сферу, для которой разрабатывалось Ваше решение.\n\n"
        "1. Медицина\n"
        "2. Образование\n"
        "3. Финансовые технологии\n"
        "4. Сельское хозяйство\n"
        "5. Туризм\n"
        "6. Спорт\n"
        "7. Транспорт и логистика\n"
        "8. Правоохранительные органы и судебная система\n"
        "9. Социальные сети и коммуникационные платформы\n"
        "10. Рекрутмент\n\n"
        "Введите номер темы:",
        reply_markup=ReplyKeyboardRemove()
    )
    return TOPIC

async def topic(update: Update, context: CallbackContext) -> int:
    topic_num = update.message.text.strip()
    if topic_num not in data['topics']:
        await update.message.reply_text("Пожалуйста, введите корректный номер темы (1-10):")
        return TOPIC
    
    context.user_data['topic'] = topic_num
    context.user_data['metrics'] = {str(i): 0 for i in range(1, 7)}  
    context.user_data['current_metric'] = 1
    context.user_data['current_question'] = 0
    
    await update.message.reply_text(
        f"Вы выбрали тему: {data['topics'][topic_num]}\n\n"
        "Начинаем оценку. Отвечайте 'да' или 'нет' на вопросы.\n\n"
        f"Метрика 1: {data['metrics']['1']}\n"
        f"Вопрос 1: {data['questions'][topic_num]['1'][0]}"
    )
    return QUESTION

async def question(update: Update, context: CallbackContext) -> int:
    user_answer = update.message.text.lower().strip()
    if user_answer not in ['да', 'нет']:
        await update.message.reply_text("Пожалуйста, отвечайте только 'да' или 'нет'.")
        return QUESTION
    
    topic_num = context.user_data['topic']
    current_metric = str(context.user_data['current_metric'])
    current_question = context.user_data['current_question']
    
    if user_answer == 'да':
        context.user_data['metrics'][current_metric] += 1
    
    current_question += 1
    if current_question < 10:
        context.user_data['current_question'] = current_question
        await update.message.reply_text(
            f"Метрика {current_metric}: {data['metrics'][current_metric]}\n"
            f"Вопрос {current_question + 1}: {data['questions'][topic_num][current_metric][current_question]}"
        )
        return QUESTION
    else:
        next_metric = int(current_metric) + 1
        if next_metric <= 6:
            context.user_data['current_metric'] = next_metric
            context.user_data['current_question'] = 0
            await update.message.reply_text(
                f"Метрика {next_metric}: {data['metrics'][str(next_metric)]}\n"
                f"Вопрос 1: {data['questions'][topic_num][str(next_metric)][0]}"
            )
            return QUESTION
        else:
            result = await calculate_results(update, context)  
            await update.message.reply_text(f"Результат: {result}")
            return ConversationHandler.END  

async def calculate_results(update: Update, context: CallbackContext) -> int:
    topic_num = context.user_data['topic']
    metrics = context.user_data['metrics']
    weights = data['weights'][topic_num]
    
    total_score = 0
    results_text = "Результаты оценки:\n\n"
    
    for metric_num, yes_count in metrics.items():
        percentage = (yes_count / 10) * 100
        score = 0
        if percentage <= 10:
            score = 0
        elif 10 < percentage <= 30:
            score = 1
        elif 30 < percentage <= 50:
            score = 2
        elif 50 < percentage <= 70:
            score = 3
        elif 70 < percentage <= 90:
            score = 4
        else:
            score = 5
        
        weighted_score = score * weights[metric_num]
        total_score += weighted_score
        
        results_text += (
            f"{data['metrics'][metric_num]}:\n"
            f"- Ответов 'да': {yes_count}/10 ({percentage:.0f}%)\n"
            f"- Оценка: {score}/5\n"
            f"- Взвешенная оценка: {weighted_score:.2f}\n\n"
        )
    
    results_text += f"Итоговый балл: {total_score:.2f}/5\n\n"
    
    if total_score < 3.5:
        results_text += "Ваше решение не является этичным и должно быть доработано."
    else:
        results_text += "Ваше решение этично!"
    
    await update.message.reply_text(results_text)
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "Оценка прервана. Если хотите начать заново, введите /start.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

from telegram.ext import Application

def main() -> None:
    application = Application.builder().token("7626673163:AAHIb21LOUCp98Prh8OEfNC27DAfpryjWWo").build()
    dispatcher = application

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, topic)],
            QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, question)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()