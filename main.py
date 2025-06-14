import action_chain
import util

if __name__ == '__main__':
    action_chain = action_chain.ActionChain()

    action_handle = action_chain.add_action()
    action_handle.add_prompt_user("Spell your firstname for me")
    action_handle.add_get_user_input(util.INPUT_TYPE.SPELLING, print)
    action_handle.add_confirm_user_input("Did I understand you correctly, your firstname is")

    action_handle = action_chain.add_action()
    action_handle.add_prompt_user("Where do you live?")
    action_handle.add_get_user_input(util.INPUT_TYPE.PLACE, print)
    action_handle.add_confirm_user_input("Did I understand you correctly, your live in")


    action_chain.run()



