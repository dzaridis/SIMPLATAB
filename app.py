import os
import pandas as pd
import yaml
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, send_file
from werkzeug.utils import secure_filename
import tempfile
import shutil
from Helpers import io_paths
from Helpers.pipelines_main import train_k_fold, external_test, read_yaml
from Helpers.data_checks import DataChecker
from Helpers import DBDM
import zipfile
import io
import shutil
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.middleware.dispatcher import DispatcherMiddleware

app = Flask(__name__, template_folder='templates')

root_app = Flask(__name__)
@root_app.route('/')
def root_redirect():
    return redirect('/automl/')

app.wsgi_app = ProxyFix(app.wsgi_app)
application = DispatcherMiddleware(root_app, {
    '/automl': app.wsgi_app
})

# Create temporary directories for input and output
TEMP_INPUT_FOLDER = os.path.join(tempfile.gettempdir(), 'ml_app_input')
TEMP_OUTPUT_FOLDER = os.path.join(tempfile.gettempdir(), 'ml_app_output')
os.makedirs(TEMP_INPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_OUTPUT_FOLDER, exist_ok=True)

# UI mode writes pipeline artefacts under <TEMP_OUTPUT_FOLDER>/Materials so that
# the same code path works for both the EUCAIM headless mode (--output dir) and
# the legacy Flask UI mode (no /app write access for the eucaim user).
MATERIALS_DIR = os.environ.get(
    "SIMPLATAB_OUTPUT_DIR",
    os.path.join(TEMP_OUTPUT_FOLDER, "Materials"),
)
io_paths.set_output_base(MATERIALS_DIR)
os.makedirs(os.path.join(MATERIALS_DIR, "Models"), exist_ok=True)

# Configure upload settings
ALLOWED_EXTENSIONS = {'csv', 'yaml'}
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    # Clear temporary folders
    for folder in [TEMP_INPUT_FOLDER, TEMP_OUTPUT_FOLDER]:
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
    
    # Check if files were uploaded
    if 'train_file' not in request.files or 'test_file' not in request.files:
        flash('Missing required files')
        return redirect(request.url)
    
    train_file = request.files['train_file']
    test_file = request.files['test_file']
    
    # Check if filenames are valid
    if train_file.filename == '' or test_file.filename == '':
        flash('No selected files')
        return redirect(request.url)
    
    if not (allowed_file(train_file.filename) and allowed_file(test_file.filename)):
        flash('Invalid file type. Only CSV files are allowed.')
        return redirect(request.url)
    
    # Save files
    train_file.save(os.path.join(TEMP_INPUT_FOLDER, 'Train.csv'))
    test_file.save(os.path.join(TEMP_INPUT_FOLDER, 'Test.csv'))
    
    # Redirect to parameters page
    return redirect('/automl/parameters')

@app.route('/parameters', methods=['GET', 'POST'])
def parameters():
    if request.method == 'POST':
        # Get parameters from form
        params = {}
        params["BiasAssessment"] = request.form.get('bias_assessment') == 'true'
        params["Feature"] = request.form.get('feature')
        params["number_of_k_folds"] = int(request.form.get('k_folds'))
        
        params["apply_grid_search"] = {}
        params["apply_grid_search"]["enabled"] = request.form.get('grid_search') == 'true'
        params["apply_grid_search"]["type"] = {}
        randomized = request.form.get('grid_search_type') == 'randomized'
        params["apply_grid_search"]["type"]["Randomized"] = randomized
        params["apply_grid_search"]["type"]["Exhaustive"] = not randomized
        
        params["Correlation Limit"] = float(request.form.get('correlation_limit'))
        params["Metric For Threshold Optimization"] = request.form.get('optimization_metric')
        
        params["Machine Learning Models"] = {}
        params["Machine Learning Models"]["Logistic Regression"] = request.form.get('logistic_regression') == 'true'
        params["Machine Learning Models"]["Support Vector Machines"] = request.form.get('svm') == 'true'
        params["Machine Learning Models"]["Random Forest"] = request.form.get('random_forest') == 'true'
        params["Machine Learning Models"]["Stochastic Gradient Descent"] = request.form.get('sgd') == 'true'
        params["Machine Learning Models"]["Multi-Layer Neural Network"] = request.form.get('neural_network') == 'true'
        params["Machine Learning Models"]["Decision Trees"] = request.form.get('decision_trees') == 'true'
        params["Machine Learning Models"]["XGBoost"] = request.form.get('xgboost') == 'true'
        
        # Save YAML file
        yaml_path = os.path.join(TEMP_INPUT_FOLDER, "machine_learning_parameters.yaml")
        with open(yaml_path, 'w') as file:
            yaml.dump(params, file)
        
        # Run the machine learning pipeline
        run_pipeline(TEMP_INPUT_FOLDER, TEMP_OUTPUT_FOLDER, params)
        
        return redirect('/automl/results')
    
    # Check if we have multiclass data
    is_multiclass = False
    num_classes = 2
    class_distribution = {}
    
    try:
        # Try to load and check the training data
        train_path = os.path.join(TEMP_INPUT_FOLDER, "Train.csv")
        if os.path.exists(train_path):
            train_df = pd.read_csv(train_path)
            if 'Target' in train_df.columns:
                unique_classes = train_df['Target'].unique()
                num_classes = len(unique_classes)
                is_multiclass = num_classes > 2
                
                # Get class distribution
                class_counts = train_df['Target'].value_counts().to_dict()
                total = len(train_df)
                class_distribution = {
                    cls: {
                        'count': count,
                        'percentage': round(count / total * 100, 2)
                    } for cls, count in class_counts.items()
                }
    except Exception as e:
        print(f"Error detecting multiclass: {e}")
    
    return render_template(
        'parameters.html', 
        is_multiclass=is_multiclass, 
        num_classes=num_classes,
        class_distribution=class_distribution
    )

@app.route('/results')
def results():
    result_files = []

    # Detect if multiclass
    is_multiclass = False
    try:
        test_results_path = os.path.join(MATERIALS_DIR, "test_results.xlsx")
        if os.path.exists(test_results_path):
            test_results = pd.read_excel(test_results_path)
            if 'Number of Classes' in test_results.columns:
                num_classes = test_results['Number of Classes'].iloc[0]
                is_multiclass = num_classes > 2
    except Exception as e:
        print(f"Error detecting multiclass in results: {e}")

    if os.path.exists(MATERIALS_DIR):
        for root, dirs, files in os.walk(MATERIALS_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, MATERIALS_DIR)
                # Templates expect a "Materials/<rel>" prefix so that the
                # download route can locate the file.
                result_files.append({
                    'name': rel_path,
                    'path': os.path.join("Materials", rel_path).replace("\\", "/"),
                })

    return render_template('results.html', result_files=result_files, is_multiclass=is_multiclass)

@app.route('/download/<path:filepath>')
def download_file(filepath):
    # The template emits "Materials/<rel>" — strip the leading segment and
    # serve from the configured MATERIALS_DIR.
    parts = filepath.split('/')
    if parts and parts[0] == "Materials":
        parts = parts[1:]
    rel = os.path.join(*parts) if parts else ""
    target = os.path.join(MATERIALS_DIR, rel)
    directory = os.path.dirname(target)
    filename = os.path.basename(target)

    print(f"Attempting to download from: {directory}, file: {filename}")

    return send_from_directory(directory, filename, as_attachment=True)

@app.route('/download_all')
def download_all():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(MATERIALS_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, MATERIALS_DIR)
                zipf.write(file_path, arcname)
    memory_file.seek(0)

    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='pipeline_results.zip'
    )


@app.route('/clear_files', methods=['POST'])
def clear_files():
    if os.path.exists(MATERIALS_DIR):
        for root, dirs, files in os.walk(MATERIALS_DIR, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error removing {file_path}: {e}")
            if root != MATERIALS_DIR:
                try:
                    os.rmdir(root)
                except Exception as e:
                    print(f"Error removing directory {root}: {e}")

    os.makedirs(os.path.join(MATERIALS_DIR, "Models"), exist_ok=True)
    return redirect('/automl/results')


def run_pipeline(input_folder, output_folder, params):
    try:
        read_yaml(input_folder)

        # Perform Bias Assessment
        if params["BiasAssessment"]:
            print("------------- \n", " Bias Detection Started \n", "-------------")
            try:
                print("------------- \n", " Bias Detection Started for Train.csv \n", "-------------")
                DBDM.bias_config(
                    file_path=os.path.join(input_folder, "Train.csv"),
                    subgroup_analysis=0,  # default is 0
                    facet=params["Feature"],
                    outcome='Target',
                    subgroup_col='',  # default is ''
                    label_value=1,  # default is 1
                )
                print("------------- \n", " Bias Detection Finished for Train.csv \n", "-------------")
            except Exception as e:
                print(f"Error in bias detection for Train.csv: {e}")
            
            try:
                print("------------- \n", " Bias Detection Started for Test.csv \n", "-------------")
                DBDM.bias_config(
                    file_path=os.path.join(input_folder, "Test.csv"), 
                    subgroup_analysis=0, # default is 0
                    facet=params["Feature"],
                    outcome='Target',
                    subgroup_col='',  # default is ''
                    label_value=1,  # default is 1
                )
                print("------------- \n", " Bias Detection Finished for Test.csv \n", "-------------")
            except Exception as e:
                print(f"Error in bias detection for Test.csv: {e}")

        # Load data
        print("------------- \n", "Loading Data \n", "-------------")
        data_checker = DataChecker(input_folder)

        # Process the data
        try:
            train, test = data_checker.process_data()
            print("Train and Test data processed successfully.")
        except FileNotFoundError as e:
            print(e)
            return f"Error: {e}"
        except ValueError as e:
            print(e)
            return f"Error: {e}"

        X_train = train.drop('Target', axis=1)
        y_train = train['Target']
        X_test = test.drop('Target', axis=1)
        y_test = test['Target']
        print("------------- \n", "Data Loaded successfully \n", "-------------")

        # Run the pipeline
        print("------------- \n", "Training on K-Fold cross validation \n", "-------------")
        params_dict, scores_storage, thresholds, _ = train_k_fold(X_train, y_train)
        print("------------- \n", "Training on K-Fold cross validation completed successfully \n", "-------------")

        print("------------- \n", "Evaluating algorithms on Test.csv \n", "-------------")
        external_test(X_train, y_train, X_test, y_test, params_dict, thresholds)
        print("Pipeline completed successfully.")
        return "Pipeline completed successfully"
    
    except Exception as e:
        print(f"Error in pipeline: {e}")
        return f"Error: {e}"


if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 5000, application, use_debugger=True)