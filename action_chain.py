import util
import voice_util as vu

class Action:
    _prev_action = None
    _next_action = None

    _prompt_user_text = None
    _prompt_user_side_effect_func = None
    _categories = None
    _categories_side_effect_func = None
    _user_input_type = None
    _user_input_side_effect_func = None
    _help_message = None
    _help_message_side_effect_func = None
    _HELP = "help, no understanding"
    _confirm_user_input_message = None

    _RETURN = "take me to the previous field"
    _PROCEED = "continue"
    _navigation_categories = [_RETURN, _PROCEED]

    _CORRECT = "yes"
    _WRONG = "no"
    _confirmation_categories = [_CORRECT, _WRONG]


    # public methods

    def __init__(self, prev_action):
        self._prev_action = prev_action
    
    def add_prev_action(self, prev_action):
        self._prev_action = prev_action
    
    def add_next_action(self, next_action):
        self._next_action = next_action

    def add_prompt_user(self, text):
        """
        Tell the user what to do at the beginning of a new action
        :param text: instruction to user
        :return:
        """
        self._prompt_user_text = text

    def add_get_user_input(self, user_input_type, side_effect_func=None):
        """
        Get user input from voice, the input is categorized based on user_input_type
        :param user_input_type:
        :param side_effect_func:
        :return:
        """
        self._user_input_type = user_input_type
        self._user_input_side_effect_func = side_effect_func

    def add_confirm_user_input(self, message):
        """
        After receiving the user input, play a message to confirm their selection
        :param message: Should be of the form: Did you say this [user answer]
        :return:
        """
        self._confirm_user_input_message = message

    def add_help(self, message):
        """
        If the user asks for help, play message
        :param message: e.g. "A BSN is bla bla bla, you need to give me an 8 digit number"
        :return:
        """
        self._help_message = message

    def run(self):
        """
        Execute the action
        :return:
        """
        user_confirmation = self._WRONG
        # Prompts the user with a question until they have confirmed, that they have been understood correctly
        while user_confirmation == self._WRONG:
            self._execute_conditional(self._prompt_user_text, vu.say)
            input_text = self._execute_conditional(self._user_input_type, vu.get_user_input, self._user_input_side_effect_func)

            self._execute_conditional(self._confirm_user_input_message + input_text, vu.say)
            user_confirmation = self._execute_conditional(self._confirmation_categories, vu.categorize_user_input)
            if user_confirmation == self._WRONG:
                self._execute_conditional("Sorry, lets try that again", vu.say)

        # Continue with the application
        self._execute_conditional("Splendid. Lets continue.", vu.say)

        # TODO: Figure out a natural way to move between question
        '''
        self._execute_conditional("Do you want to continue the application or return to the previous field?")
        user_action = self._execute_conditional(self._navigation_categories, vu.categorize_user_input, self._categories_side_effect_func)
        
        if user_action == self._RETURN:
            if self._prev_action is None:
                self._execute_conditional("Sorry, this is the first field. Lets continue with the next field", vu.say)
            else:
                self._prev_action.run()
        '''

        # Ececute the next action
        if self._next_action is not None:
            self._next_action.run()

    # private methods

    def _execute_conditional(self, param, func, side_effect_func=None):
        """
        This function is used to execute function like "add_user_input, add_help, ..." only if they have been set
        :param param: Parameters required to run func, e.g. the type of user input
        :param func: add_user_input, add_help, ...
        :param side_effect_func: A function that uses the output of func
        :return:
        """
        result = None
        if param is not None:
            result = func(param)
            if side_effect_func:
                # e.g. side_effect_func can be used to fill out a pdf form with the user input obtained from func
                side_effect_func(result)
        return result


class ActionChain:
    """
    A doubly connected linked list consisting of actions
    """
    def __init__(self):
        self._head = None
        self._tail = None

    def add_action(self):
        new_action = Action(self._tail)
        if self._head is None:
            self._head = new_action
        else:
            self._tail.add_next_action(new_action)
        self._tail = new_action
        return new_action

    def run(self):
        if self._head is not None:
            self._head.run()



