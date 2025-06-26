import util
import voice_util as vu


class Action:
    _prev_action = None
    _next_action = None
    _action_completed = False

    _prompt_user_text = None
    _prompt_user_side_effect_func = None
    _categories = None
    _categories_side_effect_func = None
    _user_input_type = None
    _user_input_side_effect_func = None
    _confirm_user_input_message = None

    _YES = "yes"
    _NO = "no"
    _confirmation_categories = [_YES, _NO]


    # public methods

    def __init__(self, prev_action):
        self._prev_action = prev_action

    def get_prompt_user_text(self):
        return self._prompt_user_text

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

    def _get_navigation_input(self, message):
        self._execute_conditional(message, vu.say)
        return self._execute_conditional(self._confirmation_categories, vu.categorize_user_input,
                                                self._categories_side_effect_func)

    def run(self):

        """
        Execute the action
        :return:
        """

        user_confirmation = self._NO
        # Prompts the user with a question until they have confirmed, that they have been understood correctly
        while user_confirmation == self._NO:
            # Prompt user with action they need to perform
            self._execute_conditional(self._prompt_user_text, vu.say)

            # Prompt user if they want to skip the action if they have completed it before
            # if self._action_completed:
            #    skip = self._get_navigation_input("You have completed this action already, do you want to skip it?")
            #    if skip == self._YES:
            #        break

            # Get the user answer
            input_text = self._execute_conditional(self._user_input_type, vu.get_user_input, self._user_input_side_effect_func)

            # Confirm user answers

            # Space digits if input is a bsn or some other number that is not a year
            input_text_s = self._user_input_type.format(input_text)

            if self._confirm_user_input_message is not None:
                user_confirmation = self._get_navigation_input(self._confirm_user_input_message + str(input_text_s))
                if user_confirmation == self._NO:
                    self._execute_conditional("Sorry, lets try that again", vu.say)
            else:
                user_confirmation = self._YES

        #if self._prev_action is not None:
        #    user_confirmation = self._get_navigation_input(f"Would you like to return to the previous action? It was: {self._prev_action.get_prompt_user_text()}")
        #    if user_confirmation == self._YES:
        #        self._execute_conditional("Okay, lets take one step back", vu.say)
        #        self._prev_action.run()

        # Continue with the next action
        if self._next_action is not None:
            self._execute_conditional("Splendid. Lets continue.", vu.say)
            self._action_completed = True
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



