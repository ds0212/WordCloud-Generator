from bs4 import BeautifulSoup as soup
import urllib
import requests
import pandas as pd
import time
import os
from flask import Flask, render_template, session, redirect, request
from flask_cors import CORS, cross_origin
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import ssl

# Global paths for images and csv folders.

IMG_FOLDER = os.path.join("static", "images")
CSV_FOLDER = os.path.join("static", "CSVs")

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

app.config['IMG_FOLDER'] = IMG_FOLDER
app.config['CSV_FOLDER'] = CSV_FOLDER

# ssl certificate verification
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context


class DataCollection:
    """
    Management and collection of data
    """

    def __init__(self):
        """Initializing dictionary to gather the data"""
        self.data = {"Product": list(),
                     "Name": list(),
                     "Price": list(),
                     "Rating": list(),
                     "Comment Heading": list(),
                     "Comment": list()
                     }

    def get_final_data(self, commentbox=None, prodname=None, prodprice=None):
        """Appending gathered data from comment box to dictionary"""
        self.data["Product"].append(prodname)
        self.data["Price"].append(prodprice)
        try:
            # Append the name of the customer if exists
            self.data["Name"].append(commentbox.div.div.\
				find_all('p', {'class': '_2sc7ZR _2V5EHH'})[0].text)
        except Exception as e:
            self.data["Name"].append("No Name")

        try:
            # Append rating given by the customer
            self.data["Rating"].append(commentbox.div.div.div.div.text)
        except Exception as e:
            self.data["Rating"].append("No Rating")

        try:
            # Append Heading of comment by the customer if exists
            self.data["Comment Heading"].append(commentbox.div.div.div.p.text)
        except Exception as e:
            self.data["Comment Heading"].append('No Comment Heading')

        try:
            # Append comments of the customer if exists
            comtag = commentbox.div.div.find_all('div', {'class': ''})
            self.data["Comment"].append(comtag[0].div.text)
        except Exception as e:
            self.data["Comment"].append('')

    def get_main_HTML(self, base_URL=None, search_string=None):
        """Return HTML page based on the search string"""
        # Search URL based upon base_URL and search_string
        search_url = f"{base_URL}/search?q={search_string}"
        # Reading the contents of the page
        with urllib.request.urlopen(search_url) as url:
            page = url.read()
        # Returning parsed page using bs4
        return soup(page, "html.parser")

    def get_product_name_links(self, flipkart_base=None, big_boxes=None):
        """Returns the list of (Product name, Product link)"""
        # Declaring temporary list
        temp = []
        # Iterating through the list
        for box in big_boxes:
            try:
                # Appending product name and link if present
                temp.append((box.div.div.div.a.img['alt'],
                             flipkart_base + box.div.div.div.a["href"]))
            except Exception as e:
                pass

        return temp

    def get_prod_HTML(self, product_link=None):
        """Returns each product's HTML page after parsing"""
        prod_page = requests.get(product_link)
        return soup(prod_page.text, "html.parser")

    def get_data_dict(self):
        """Returns collected data in dictionary"""
        return self.data

    def save_as_dataframe(self, dataframe, file_name=None):
        """Saves the dictionary as csv and returns the final path of the csv"""
        csv_path = os.path.join(app.config["CSV_FOLDER"], file_name)
        file_extension = ".csv"
        final_path = f"{csv_path}{file_extension}"
        # Cleaning previously stored files
        CleanCache(directory=app.config["CSV_FOLDER"])
        dataframe.to_csv(final_path, index=None)
        print("File saved successfully.")
        return final_path

    def save_wordcloud_image(self, dataframe=None, img_filename=None):
        """Generates and saves wordcloud images to the folder"""
        # Extracts all the comments
        txt = dataframe["Comment"].values
        # Generate wordcloud
        wc = WordCloud(width=800, height=400, background_color="black", stopwords=STOPWORDS).generate(str(txt))
        plt.figure(figsize=(20, 10), facecolor='k', edgecolor='k')
        plt.imshow(wc, interpolation='bicubic')
        plt.axis('off')
        plt.tight_layout()
        # Creating path
        img_path = os.path.join(app.config["IMG_FOLDER"], img_filename + ".png")
        # Cleaning previously stored images
        CleanCache(directory=app.config["IMG_FOLDER"])
        # Save the image file to image path
        plt.savefig(img_path)
        plt.close()
        print("Saved wordcloud image.")


class CleanCache:
    """
    Responsible to clean any residual image or file present inside a directory.
    """

    def __init__(self, directory=None):
        self.clean_path = directory
        # Proceeding only if directory is not empty
        if os.listdir(self.clean_path) != list():
            # Iteration over the files to be removed
            files = os.listdir(self.clean_path)
            for filename in files:
                print(filename)
                os.remove(os.path.join(self.clean_path, filename))
        print("Cleaned.")


# Route to display home page
@app.route("/", methods=["GET"])
@cross_origin()
def homePage():
    return render_template("index.html")


# Route to display review page
@app.route("/review", methods=["GET", "POST"])
@cross_origin()
def index():
    if request.method == "POST":
        try:
            # Get base URL and search string
            base_URL = 'https://www.flipkart.com'  # 'https://www.' + input("enter base URL: ")
            # Enter a product name eg "iphone 13"
            search_string = request.form["content"]
            search_string = search_string.replace(" ", "+")
            print('Processing...')

            # Counter to start counting time in seconds
            start = time.perf_counter()
            getdata = DataCollection()

            # Store main HTML page for given search query
            flipkart_HTML = getdata.get_main_HTML(base_URL, search_string)

            # Store all the boxes containing products
            bigboxes = flipkart_HTML.find_all("div", {"class": "_1AtVbE col-12-12"})

            # Store extracted product name links
            product_name_links = getdata.get_product_name_links(base_URL, bigboxes)

            # Iterating over the list of product names and links
            for prodname, productlink in product_name_links[:4]:
                # Iterate over HTML
                for prod_HTML in getdata.get_prod_HTML(productlink):
                    try:
                        # Extract comment boxes from product HTML
                        comment_boxes = prod_HTML.find_all('div', {'class': '_16PBlm'})  # _3nrCtb
                        prod_price = prod_HTML.find_all('div', {"class": "_30jeq3 _16Jk6d"})[0].text
                        prod_price = float((prod_price.replace("₹", "")).replace(",", ""))
                        # Iterate over comment boxes to extract required data
                        for commentbox in comment_boxes:
                            # Prepare final data
                            getdata.get_final_data(commentbox, prodname, prod_price)
                    except:
                        pass
            # Save the data gathered in a dataframe
            df = pd.DataFrame(getdata.get_data_dict())

            # Save dataframe as a csv to be downloaded
            download_path = getdata.save_as_dataframe(df, file_name=search_string.replace("+", "_"))

            # Generate and save wordcloud image
            getdata.save_wordcloud_image(df,
                                         img_filename=search_string.replace("+", "_"))

            finish = time.perf_counter()
            print(f"Program finished with timelapse: {finish - start} second(s)")
            return render_template("review.html",
                                   tables=[df.to_html(classes='data')],  # Pass the df as html
                                   titles=df.columns.values,  # Pass headers of each cols
                                   search_string=search_string,  # Pass the search string
                                   download_csv=download_path  # Pass the download path for csv
                                   )

        except Exception as e:
            print(e)
            # Return 404 page if error occurs
            return render_template("404.html")

    else:
        return render_template("index.html")


@app.route('/show')
@cross_origin()
def show_wordcloud():
    img_file = os.listdir(app.config['IMG_FOLDER'])[0]
    full_filename = os.path.join(app.config['IMG_FOLDER'], img_file)
    return render_template("show_wc.html", user_image=full_filename)


if __name__ == '__main__':
    app.run(debug=True)
