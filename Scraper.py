import asyncio
from playwright.async_api import async_playwright
import re
from difflib import SequenceMatcher
#import dns.resolver
import mysql.connector


async def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()
            

async def format_name (name):
    name = name.lower()
    list_name = name.split(" ")
    pattern = re.compile(r'\bInc\.?\b', flags=re.IGNORECASE)
    for x in enumerate(list_name):
        if pattern.match(x[1]):
            list_name.pop(x[0])

    return " ".join(list_name)


async def validate_company_name(name, email):
    email_split =  email.split('@')           
    base_domain = email_split[0]
    email_name = email_split[1]
    base_domain = base_domain.split('.')[0]

    # Normalize company name and domain for comparison
    company_name_normalized = name.lower().replace(' ', '')
    base_domain_normalized = base_domain.lower().replace(' ', '')

    # Calculate similarity
    similarity = await similar(company_name_normalized, base_domain_normalized)
    if similarity < 0.55:
         similarity = await similar(company_name_normalized, email_name )
    #print(similarity)
    return similarity  


async def second_valdiate (name, company_email): 
    list_result= []
    list_name = name.split(" ")
    for n in list_name:
        result = await validate_company_name(n, company_email)
        list_result.append(result)
    average =  sum(list_result) / len(list_result)
    return average


# function to format the email if it's an array or a object NONE
async def email_found_formating(found_emails):
    if found_emails:    
        if isinstance(found_emails, list):

            
            
            #Look if one of the email contains the words info
                print("This is found emails", found_emails)
                for email in found_emails:
                    # Split the Current email to get the first part
                    split_email =  email.split("@")
                    # look if one on the emails contains this
                    if split_email[0] == "info" or "admin":
                        return email

                # If no email found with key words return the first email     
                return found_emails[0]
        
        # If there it's not a list but a str
        else:
            return found_emails
    else:
        found_emails = "INVALID"
        return found_emails

# One big verification function to match all of them in one
async def verification_email(emails, comapny_name):
    # Sort the email 
    verif_email = await email_found_formating(emails)
    if verif_email == "INVALID":
        treshold = 0
        return verif_email, treshold

    verif_email = await format_name(verif_email)

    result = await validate_company_name(comapny_name, verif_email)

    if result >= 0.55:

        return verif_email, result
    else: 
        result = await second_valdiate(comapny_name, verif_email)
        if result >= 0.55:
            print(verif_email)
            return verif_email, result
        else: 

            verif_email = "INVALID"
            treshold = 0
            print(verif_email)
            return verif_email, treshold
    


# get the Facebook info
async def get_facebook_info(company_name):
    async with async_playwright() as p:
        try: 
            browser = await p.chromium.launch(headless=False)  # Set headless=True for headless mode
            context = await browser.new_context(storage_state="facebookcookie.json")
            page = await context.new_page()

            await page.goto(f"https://www.google.com/search?q={company_name}")

        #wait the page 
            await page.wait_for_selector('div#search')
            page_content = await page.content()

            facebook_pattern = re.compile(r"https:\/\/www\.facebook\.com\/[a-zA-Z0-9\.\-\/_]+")
            facebook_links = facebook_pattern.findall(page_content)
    
            if facebook_links:
                facebook_link = facebook_links[0]  # Take the first match if multiple found
                # Go to the Facebook page
                await page.goto(facebook_link)
                
                # Wait for the Facebook page to load
                await page.wait_for_selector('body')

                # Extract email 
                page_content = await page.content()

                email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

                company_emails = email_pattern.findall(page_content)

                # Extract Phone

                phone_pattern = re.compile(r"^[0-9]{3}-[0-9]{3}-[0-9]{4}$")
                found_phone = re.findall(phone_pattern, page_content)


                founds_infos = {
                     "email" : company_emails,
                     "phone": found_phone or None
                }

                return founds_infos
        # If there is no facebook links return None
            return None

        except:
             return None






def get_database():
    mydb = mysql.connector.connect(
   host="localhost",
    user="root",
    password="root",
    database="leads"
    )
    # Dataabse query to get information about the leads without a email
    query = 'Select DISTINCT localisation.telephone, localisation.email, localisation.treshold, name.Nom, localisation.id from localisation Inner JOIN name on localisation.neq = name.NEQ and localisation.email is NULL LIMIT 70;'

    mycursor = mydb.cursor()
    mycursor.execute(query)
    rows= mycursor.fetchall()
    print(rows)
    
    return rows



# Updating the database with the what we found
def update_database(lead_id, email, treshold, telephone):
    mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="leads"
    )
        
    
    #Get the ID###############################################
    query =f"Update localisation set email = '{email}', treshold = {treshold}, telephone = {telephone}  where id= {lead_id};"
    print(query)
    mycursor = mydb.cursor()

    mycursor.execute(query)
    
    mydb.commit()
    mydb.close()
    return




    # List of companies to search for

'''
# Old version
async def get_website_contact(website):
           async with async_playwright() as p:
                # trr
                browser = await p.chromium.launch(headless=False)  # Set headless=True for headless mode
                page =  await browser.new_page()
                
                urls = []
                await page.goto(website)
                regex_email =  re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
                
                page = await page.content()
                email_home = regex_email.findall(page)
                for li in await page.get_by_text("Contact").all():
                    await li.click()
                    curr_page = await page.content()
                    email = regex_email.findall(curr_page) 
                    
                #if Contact:
                    #Contact = await page.get_by_text("Contact").click()

                await browser.close()
                return email_home, email
'''




# Function to get the website url

async def get_website_url(company_name):
           async with async_playwright() as p:
                try:
                    browser = await p.chromium.launch(headless=False)  # Set headless=True for headless mode
                    page =  await browser.new_page()

                    await page.goto(f"https://www.google.com/search?q={company_name}")
                


            # Extraire toutes les URLs des résultats de recherche
                    
                    
                    
                    #wait for the pages to load
                    await page.wait_for_selector('h3')

                    #get the first link
                    first_link = await page.query_selector('h3')

                    # Click on the first link
                    await first_link.click()
                        
                    # Await for the page to laod
                    await page.wait_for_timeout(5000)

                    page_url = page.url
                    

                    return page_url
                except:
                     print("This is the URL")
                     return None






# get the contact email
async def get_website_info(website):
           async with async_playwright() as p:
                # Launch browser
                founds_infos = {"email": "INVALID", "phone": None} 
                #If no Url is FOUND
                if not website:
                     return founds_infos
               
                try:
                    browser = await p.chromium.launch(headless=False)  # Set headless=True for headless mode
                    page =  await browser.new_page()
                

                    # Go to website and wait for page to load main page
                    
                    await page.goto(website)
                    page_content = await page.content()

                    # Search regex pattern in my html content
                    pattern = '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    found_emails = re.findall(pattern, page_content)
                    phone_pattern = re.compile(r"^[0-9]{3}-[0-9]{3}-[0-9]{4}$")
                    found_phone = re.findall(phone_pattern, page_content)
                    # Search for contact page if the email not found
                    if not found_emails:
                        
                            
                            
                        contact_button = await page.query_selector("button[name='Contact']")
                        if contact_button and await contact_button.is_visible():
                            await contact_button.click()
                            await page.wait_for_timeout(1000)
                            contact_page_content = await page.content()
                            found_emails = re.findall(pattern, contact_page_content)

                    if found_emails:
                        founds_infos["email"] = found_emails
                        founds_infos["phone"] = found_phone[0] if found_phone else None
                        
                        

                except:
                     
                    print("There was an error")

                    return founds_infos
                
              


async def main():


    leads = get_database()
    
    for lead in leads:
        #Each lead is a list
        # try with facebook
        print(lead)
        facebook_info = await get_facebook_info(lead[3])
        print(facebook_info)
        if facebook_info:
            # Process of verification
            lead_result = await verification_email(facebook_info["email"], lead[3])
            
            # Update database

            update_database(lead[4], lead_result[0], lead_result[1],facebook_info["phone"] or "NULL" )

             
        else:

            website_url = await get_website_url(lead[3])
            website_info = await get_website_info(website_url)
            print("This iss web info",website_info)
            lead_result = await verification_email(website_info["email"], lead[3])
            update_database(lead[4], lead_result[0], lead_result[1], "NULL")
            

    return "End of the script"

# Run the script

asyncio.run(main())



