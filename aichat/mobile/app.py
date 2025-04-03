from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from core.ai_chat import process_input
import asyncio


class AIChatApp(App):
    def build(self):
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        self.input_field = TextInput(hint_text="请输入你的问题或指令", multiline=True)
        layout.add_widget(self.input_field)

        submit_button = Button(text="提交")
        submit_button.bind(on_press=self.on_submit)
        layout.add_widget(submit_button)

        self.output_label = Label(text="结果会显示在这里", size_hint_y=None, height=200)
        layout.add_widget(self.output_label)

        return layout

    def on_submit(self, instance):
        user_input = self.input_field.text
        if user_input:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(process_input(user_input))
            self.output_label.text = f"输入: {user_input}\n{result['result']}"


if __name__ == "__main__":
    AIChatApp().run()