import action_chain
import util

from toeslagen import collect_user_data, run_calculation
from fill_pdf_document import collect_pdf_user_data, fill_pdf
from voice_util import say

if __name__ == '__main__':
    action_chain = action_chain.ActionChain()

    ########## Task 1: Filling in the form ########### 
    #user_data = collect_user_data()
    #say("Thanks. I'm now running the calculation.")
    #result = run_calculation(user_data)
    #say(result)
    #print("Result:", result)
    ##################################################

    ########## Task 3: Fill in PDF ###################
    user_data = collect_pdf_user_data()
    say("Thanks. I'm now filling in the PDF document.")
    result = fill_pdf(user_data)
    say(result)
    print("PDF filled and saved as 'filled_example.pdf'.")
    ##################################################

    action_handle = action_chain.add_action()
    action_handle.add_prompt_user("Spell your firstname for me")
    action_handle.add_get_user_input(util.INPUT_TYPE.SPELLING, print)
    action_handle.add_confirm_user_input("Did I understand you correctly, your firstname is")

    action_handle = action_chain.add_action()
    action_handle.add_prompt_user("Where do you live?")
    action_handle.add_get_user_input(util.INPUT_TYPE.PLACE, print)
    action_handle.add_confirm_user_input("Did I understand you correctly, you live in")


    action_chain.run()



