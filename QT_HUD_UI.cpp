#include <QApplication>
#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QTextEdit>
#include <QPushButton>
#include <QPixmap>
#include <QFont>
#include <Qthread>
#include <thread>
#include <QColor>
#include <QStyle>

class DataStreamer : public QObject {
    Q_OBJECT

//Streamer Class system for dynamically capturing data and using threads to check and update datafields.
//Non-functional Currently
public:
    DataStreamer(QObject *parent = nullptr) : QObject(parent) {}

    void startStreaming() {
        // Simulate data streaming
        QThread::create([this]{
            int counter = 0;
            while (true) {
                QString data = QString("Data update: %1").arg(counter++);
                emit dataChanged(data);
                std::this_thread::sleep_for(std::chrono::seconds(1)); // Simulate delay
            }
        })->start();
    }

signals:
    void dataChanged(const QString &data);
};


class SimpleUI : public QWidget {
public:

    SimpleUI(QWidget *parent = nullptr) : QWidget(parent) {
        setWindowTitle("Advanced Qt UI");
        resize(800, 600);
        setStyleSheet("background:transparent;");
        setStyleSheet("border: 4px solid black;");
        setAttribute(Qt::WA_TranslucentBackground);
        setWindowFlags(Qt::FramelessWindowHint);

        QVBoxLayout *mainLayout = new QVBoxLayout(this);
        QHBoxLayout *topLayout = new QHBoxLayout();

        QHBoxLayout *bottomLayout = new QHBoxLayout();
        QVBoxLayout *rightLayout = new QVBoxLayout();
        QFont Street_font = *new QFont();
        Street_font.setPointSize(40);
        Street_font.setUnderline(&free);
        QFont Message_font = *new QFont();
        Message_font.setPointSize(24);
        Message_font.setUnderline(&free);

        // Upper middle text box
        QLabel *upperTextBox = new QLabel();
        upperTextBox->setFixedSize(750,100);
        upperTextBox->setFont(Street_font);
        //upperTextBox->setFontWeight(72);
        //upperTextBox->setFontItalic(1);
        upperTextBox->setText("<font color=\"black\"> Next Street Name </font>");
        upperTextBox->setAlignment(Qt::AlignCenter);
        topLayout->addStretch();
        topLayout->addWidget(upperTextBox);
        topLayout->addStretch();

        // Image box in lower left
        QLabel *imageLabel = new QLabel();
        QPixmap pixmap("Arrow_Left.png"); // Replace with actual image path
        imageLabel->setPixmap(pixmap);
        imageLabel->setFixedSize(500, 500);

        // Right side text boxes moving downward
        QLabel *rightTextBox1 = new QLabel();
        rightTextBox1->setFixedSize(500,100);
        rightTextBox1->setFont(Message_font);
        //rightTextBox1->setFontWeight(100);

        //rightTextBox1->setTextColor("red");
        rightTextBox1->setText("<font color=\"red\"> <outline-color=\"black\"> High Priority Messages </font>");
        //rightTextBox1->setPlaceholderText("Right box 1");
        QLabel *rightTextBox2 = new QLabel();
        rightTextBox2->setFixedSize(500,100);
        rightTextBox2->setFont(Message_font);
        //rightTextBox2->setFontWeight(100);
        //rightTextBox2->setTextColor("gold");
        rightTextBox2->setText("<font color=\"gold\"> <outline-color=\"black\"> Medium Priority Messages </font>");
        //rightTextBox2->setPlaceholderText("Right box 2");
        QLabel *rightTextBox3 = new QLabel();
        rightTextBox3->setFixedSize(500,100);
        rightTextBox3->setFont(Message_font);
        //rightTextBox3->setFontWeight(100);
        //rightTextBox3->setTextColor("green");
        rightTextBox3->setText("<font color=\"green\"> <outline-color=\"black\"> Low Priority Messages </font>");

        //rightTextBox3->setPlaceholderText("Right box 3");

        rightLayout->addWidget(rightTextBox1);
        rightLayout->addWidget(rightTextBox2);
        rightLayout->addWidget(rightTextBox3);

        bottomLayout->addWidget(imageLabel);
        bottomLayout->addStretch();
        bottomLayout->addLayout(rightLayout);

        mainLayout->addLayout(topLayout);
        mainLayout->addStretch();
        mainLayout->addLayout(bottomLayout);
        setLayout(mainLayout);
    }
};


int main(int argc, char *argv[]) {
    QApplication app(argc, argv);
    SimpleUI window;
    window.show();
    return app.exec();
}
